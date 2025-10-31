"""
Vistas para el módulo de asistencias
Incluye vistas web y API REST
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Asistencia, ResumenDiario
from .serializers import (
    AsistenciaSerializer,
    AsistenciaListSerializer,
    CheckInSerializer,
    CheckOutSerializer,
    SincronizarAsistenciasSerializer,
    ResumenDiarioSerializer
)
from apps.trabajadores.models import Trabajador
from apps.proyectos.models import Proyecto

import csv


# ============================================
# VISTAS WEB
# ============================================

class AsistenciaListView(LoginRequiredMixin, ListView):
    model = Asistencia
    template_name = 'asistencias/lista.html'
    context_object_name = 'asistencias'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Asistencia.objects.select_related(
            'trabajador', 'proyecto', 'registrado_por'
        ).order_by('-fecha', '-hora_entrada')
        
        # Filtros
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        proyecto = self.request.GET.get('proyecto')
        estado = self.request.GET.get('estado')
        puesto = self.request.GET.get('puesto')
        llego_tarde = self.request.GET.get('llego_tarde')
        busqueda = self.request.GET.get('busqueda')
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if proyecto:
            queryset = queryset.filter(proyecto_id=proyecto)
        if estado:
            queryset = queryset.filter(estado=estado)
        if puesto:
            queryset = queryset.filter(puesto_laboral=puesto)
        if llego_tarde == 'si':
            queryset = queryset.filter(llego_tarde=True)
        if busqueda:
            queryset = queryset.filter(
                Q(trabajador__nombre__icontains=busqueda) |
                Q(trabajador__apellido__icontains=busqueda) |
                Q(trabajador__numero_cedula__icontains=busqueda)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        fecha_hoy = timezone.now().date()
        asistencias_hoy = Asistencia.objects.filter(fecha=fecha_hoy)
        
        context['stats'] = {
            'total': asistencias_hoy.count(),
            'cerrados': asistencias_hoy.filter(estado='cerrado').count(),
            'abiertos': asistencias_hoy.filter(estado='abierto').count(),
            'tarde': asistencias_hoy.filter(llego_tarde=True).count(),
            'horas_totales': asistencias_hoy.aggregate(
                total=Sum('horas_totales')
            )['total'] or 0,
            'horas_extras': asistencias_hoy.aggregate(
                total=Sum('horas_extras')
            )['total'] or 0,
        }
        
        # Para los filtros
        context['proyectos'] = Proyecto.objects.filter(activo=True)
        context['estados'] = Asistencia.ESTADO_CHOICES  # ← AHORA SÍ EXISTE
        context['puestos'] = Asistencia.objects.values_list(
            'puesto_laboral', flat=True
        ).distinct()
        
        # Filtros aplicados
        context['filtros'] = {
            'fecha_inicio': self.request.GET.get('fecha_inicio', ''),
            'fecha_fin': self.request.GET.get('fecha_fin', ''),
            'proyecto': self.request.GET.get('proyecto', ''),
            'estado': self.request.GET.get('estado', ''),
            'puesto': self.request.GET.get('puesto', ''),
            'llego_tarde': self.request.GET.get('llego_tarde', ''),
            'busqueda': self.request.GET.get('busqueda', ''),
        }
        
        # Resumen por proyecto
        context['resumen_proyectos'] = Asistencia.objects.filter(
            fecha=fecha_hoy
        ).values(
            'proyecto__nombre'
        ).annotate(
            total_asistencias=Count('id'),
            total_presentes=Count('id', filter=Q(estado='cerrado')),
            total_ausentes=Count('id', filter=Q(estado='abierto')),
            total_tarde=Count('id', filter=Q(llego_tarde=True)),
            total_horas=Sum('horas_totales'),
            total_extras=Sum('horas_extras')
        )
        
        return context

class AsistenciaDetalleView(LoginRequiredMixin, DetailView):
    """Vista de detalle de una asistencia"""
    model = Asistencia
    template_name = 'asistencias/detalle.html'
    context_object_name = 'asistencia'


class AsistenciaMarcarEntradaView(LoginRequiredMixin, View):
    """Vista para marcar entrada manualmente"""
    
    def get(self, request):
        # Filtrar trabajadores NO eliminados y con estado activo
        trabajadores = Trabajador.objects.filter(
            eliminado=False,
            estado='activo'
        ).order_by('nombre', 'apellido')
        
        # Filtrar proyectos activos (asumiendo que tienen campo 'activo')
        proyectos = Proyecto.objects.filter(activo=True).order_by('nombre')
        
        return render(request, 'asistencias/marcar_entrada.html', {
            'trabajadores': trabajadores,
            'proyectos': proyectos
        })
    
    def post(self, request):
        try:
            trabajador_id = request.POST.get('trabajador_id')
            proyecto_id = request.POST.get('proyecto_id')
            hora_entrada_str = request.POST.get('hora_entrada')
            observaciones = request.POST.get('observaciones', '')
            
            if not trabajador_id or not proyecto_id:
                messages.error(request, 'Debe seleccionar un trabajador y un proyecto')
                return redirect('asistencia_marcar_entrada')
            
            trabajador = Trabajador.objects.get(id=trabajador_id)
            proyecto = Proyecto.objects.get(id=proyecto_id)
            
            # Verificar si ya existe asistencia hoy
            fecha_hoy = timezone.now().date()
            asistencia_existente = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=fecha_hoy
            ).first()
            
            if asistencia_existente:
                messages.warning(request, f'{trabajador.nombre_completo} ya tiene una asistencia registrada hoy.')
                return redirect('asistencia_detalle', pk=asistencia_existente.id)
            
            # Procesar hora de entrada
            if hora_entrada_str:
                # Convertir string a objeto time
                from datetime import datetime
                hora_entrada = datetime.strptime(hora_entrada_str, '%H:%M').time()
            else:
                hora_entrada = timezone.now().time()
            
            # Crear asistencia
            asistencia = Asistencia.objects.create(
                trabajador=trabajador,
                proyecto=proyecto,
                fecha=fecha_hoy,
                puesto_laboral=trabajador.puesto_laboral,
                hora_entrada=hora_entrada,
                observaciones=observaciones,
                metodo_identificacion='manual',
                registrado_por=request.user,
                estado='abierto'
            )
            
            messages.success(request, f'Entrada registrada correctamente para {trabajador.nombre_completo}')
            return redirect('asistencia_detalle', pk=asistencia.id)
            
        except Trabajador.DoesNotExist:
            messages.error(request, 'Trabajador no encontrado')
            return redirect('asistencia_marcar_entrada')
        except Proyecto.DoesNotExist:
            messages.error(request, 'Proyecto no encontrado')
            return redirect('asistencia_marcar_entrada')
        except ValueError as e:
            messages.error(request, f'Error en el formato de hora: {str(e)}')
            return redirect('asistencia_marcar_entrada')
        except Exception as e:
            messages.error(request, f'Error al registrar entrada: {str(e)}')
            return redirect('asistencia_marcar_entrada')

class AsistenciaCerrarTurnoView(LoginRequiredMixin, View):
    """Vista para cerrar el turno de un trabajador"""
    
    def post(self, request, pk):
        try:
            asistencia = Asistencia.objects.get(pk=pk)
            
            # Verificar que el turno esté abierto
            if asistencia.estado != 'abierto':
                messages.warning(request, 'Este turno ya está cerrado')
                return redirect('asistencia_detalle', pk=pk)
            
            # Obtener hora de salida del formulario
            hora_salida_str = request.POST.get('hora_salida')
            observaciones_adicionales = request.POST.get('observaciones', '')
            
            # Procesar hora de salida
            if hora_salida_str:
                from datetime import datetime
                hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()
            else:
                hora_salida = timezone.now().time()
            
            # Cerrar turno usando el método del modelo
            asistencia.cerrar_turno(hora_salida=hora_salida)
            
            # Agregar observaciones si hay
            if observaciones_adicionales:
                if asistencia.observaciones:
                    asistencia.observaciones += f"\n{observaciones_adicionales}"
                else:
                    asistencia.observaciones = observaciones_adicionales
            
            # Registrar quién editó
            asistencia.editado_por = request.user
            asistencia.save()
            
            messages.success(
                request, 
                f'Turno cerrado correctamente. Horas trabajadas: {asistencia.duracion_jornada}'
            )
            return redirect('asistencia_detalle', pk=pk)
            
        except Asistencia.DoesNotExist:
            messages.error(request, 'Asistencia no encontrada')
            return redirect('asistencias_lista')
        except ValueError as e:
            messages.error(request, f'Error en el formato de hora: {str(e)}')
            return redirect('asistencia_detalle', pk=pk)
        except Exception as e:
            messages.error(request, f'Error al cerrar turno: {str(e)}')
            return redirect('asistencia_detalle', pk=pk)

class AsistenciaEditarView(LoginRequiredMixin, View):
    """Vista para editar asistencia existente"""
    
    def get(self, request, pk):
        asistencia = get_object_or_404(Asistencia, pk=pk)
        
        if not asistencia.puede_editar:
            messages.warning(request, '⚠️ Solo se pueden editar asistencias del día actual o día anterior.')
            return redirect('asistencia_detalle', pk=pk)
        
        return render(request, 'asistencias/editar.html', {
            'asistencia': asistencia,
        })
    
    def post(self, request, pk):
        asistencia = get_object_or_404(Asistencia, pk=pk)
        
        if not asistencia.puede_editar:
            messages.warning(request, '⚠️ No se puede editar esta asistencia.')
            return redirect('asistencia_detalle', pk=pk)
        
        try:
            hora_entrada = request.POST.get('hora_entrada')
            hora_salida = request.POST.get('hora_salida')
            observaciones = request.POST.get('observaciones', '')
            
            if hora_entrada:
                asistencia.hora_entrada = datetime.strptime(hora_entrada, '%H:%M').time()
            
            if hora_salida:
                asistencia.hora_salida = datetime.strptime(hora_salida, '%H:%M').time()
            
            asistencia.observaciones = observaciones
            asistencia.editado_por = request.user
            asistencia.save()
            
            messages.success(request, '✅ Asistencia actualizada correctamente.')
            return redirect('asistencia_detalle', pk=pk)
        
        except Exception as e:
            messages.error(request, f'❌ Error al editar asistencia: {str(e)}')
            return redirect('asistencia_editar', pk=pk)


class AsistenciaReportesView(LoginRequiredMixin, TemplateView):
    """Vista para generar reportes de asistencias"""
    template_name = 'asistencias/reportes.html'
    
    def get(self, request):
        # Obtener parámetros de filtro
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        proyecto_id = request.GET.get('proyecto')
        
        # Valores por defecto: mes actual
        if not fecha_inicio or not fecha_fin:
            hoy = timezone.now().date()
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        else:
            from datetime import datetime
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        # Filtrar asistencias
        asistencias = Asistencia.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('trabajador', 'proyecto')
        
        if proyecto_id:
            asistencias = asistencias.filter(proyecto_id=proyecto_id)
        
        # Estadísticas generales
        stats = {
            'total_asistencias': asistencias.count(),
            'total_trabajadores': asistencias.values('trabajador').distinct().count(),
            'horas_normales_total': asistencias.aggregate(
                total=Sum('horas_normales')
            )['total'] or 0,
            'horas_extras_total': asistencias.aggregate(
                total=Sum('horas_extras')
            )['total'] or 0,
            'llegadas_tarde': asistencias.filter(llego_tarde=True).count(),
            'salidas_temprano': asistencias.filter(salio_temprano=True).count(),
        }
        
        # Resumen por trabajador - CORREGIDO
        resumen_trabajadores = asistencias.values(
            'trabajador__id',
            'trabajador__nombre',
            'trabajador__apellido',
            'trabajador__numero_cedula',
            'puesto_laboral'
        ).annotate(
            dias_trabajados=Count('id'),
            total_horas_normales=Sum('horas_normales'),
            total_horas_extras=Sum('horas_extras'),
            total_horas=Sum('horas_totales'),
            llegadas_tarde=Count('id', filter=Q(llego_tarde=True))
        ).order_by('trabajador__nombre', 'trabajador__apellido')
        
        # Combinar nombre y apellido para cada trabajador
        for trabajador in resumen_trabajadores:
            trabajador['trabajador__nombre_completo'] = f"{trabajador['trabajador__nombre']} {trabajador['trabajador__apellido']}"
        
        # Resumen por proyecto
        resumen_proyectos = asistencias.values(
            'proyecto__nombre'
        ).annotate(
            total_asistencias=Count('id'),
            total_horas=Sum('horas_totales')
        ).order_by('proyecto__nombre')
        
        # Lista de proyectos para el filtro
        proyectos = Proyecto.objects.filter(activo=True)
        
        context = {
            'stats': stats,
            'resumen_trabajadores': resumen_trabajadores,
            'resumen_proyectos': resumen_proyectos,
            'proyectos': proyectos,
            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
            'proyecto_id': proyecto_id or '',
        }
        
        return render(request, self.template_name, context)

def asistencias_exportar_csv(request):
    """Exporta asistencias a CSV según filtros"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    proyecto_id = request.GET.get('proyecto')
    
    asistencias = Asistencia.objects.select_related('trabajador', 'proyecto').all()
    
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            asistencias = asistencias.filter(fecha__range=[fecha_inicio_obj, fecha_fin_obj])
        except:
            pass
    
    if proyecto_id:
        asistencias = asistencias.filter(proyecto_id=proyecto_id)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="asistencias_reporte.csv"'
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'Fecha',
        'Trabajador',
        'Cédula',
        'Puesto',
        'Proyecto',
        'Hora Entrada',
        'Hora Salida',
        'Horas Normales',
        'Horas Extras',
        'Horas Totales',
        'Llegó Tarde',
        'Estado',
        'Observaciones'
    ])
    
    # Datos
    for asistencia in asistencias:
        writer.writerow([
            asistencia.fecha.strftime('%d/%m/%Y'),
            asistencia.trabajador.nombre_completo,
            asistencia.trabajador.numero_cedula,
            asistencia.puesto_laboral,
            asistencia.proyecto.nombre,
            asistencia.hora_entrada.strftime('%H:%M') if asistencia.hora_entrada else '',
            asistencia.hora_salida.strftime('%H:%M') if asistencia.hora_salida else '',
            float(asistencia.horas_normales),
            float(asistencia.horas_extras),
            float(asistencia.horas_totales),
            'Sí' if asistencia.llego_tarde else 'No',
            asistencia.get_estado_display(),
            asistencia.observaciones
        ])
    
    return response


# ============================================
# API REST VIEWSET
# ============================================

class AsistenciaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el API REST de asistencias
    Usado por la app móvil y consultas web
    """
    queryset = Asistencia.objects.select_related('trabajador', 'proyecto').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AsistenciaListSerializer
        return AsistenciaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros desde query params
        fecha = self.request.query_params.get('fecha')
        trabajador_id = self.request.query_params.get('trabajador')
        proyecto_id = self.request.query_params.get('proyecto')
        estado = self.request.query_params.get('estado')
        
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha=fecha_obj)
            except:
                pass
        
        if trabajador_id:
            queryset = queryset.filter(trabajador_id=trabajador_id)
        
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset.order_by('-fecha', '-hora_entrada')
    
    @action(detail=False, methods=['post'], url_path='check-in')
    def check_in(self, request):
        """
        Endpoint para marcar entrada (check-in)
        
        POST /api/asistencias/check-in/
        Body: {
            "trabajador_cedula": "1234567890",
            "proyecto_id": 1,
            "hora_entrada": "07:30:00",  // Opcional
            "latitud": -25.2637,  // Opcional
            "longitud": -57.5759,  // Opcional
            "metodo_identificacion": "qr",  // qr, cedula, manual
            "dispositivo_id": "ABC123",
            "observaciones": ""
        }
        """
        serializer = CheckInSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Buscar trabajador
            trabajador = Trabajador.objects.get(
                numero_cedula=data['trabajador_cedula'],
                eliminado=False
            )
            
            # Buscar proyecto
            proyecto = Proyecto.objects.get(id=data['proyecto_id'])
            
            # Verificar si ya tiene asistencia hoy
            hoy = timezone.now().date()
            asistencia_existente = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=hoy,
                estado__in=['abierto', 'cerrado']
            ).first()
            
            if asistencia_existente:
                return Response(
                    {
                        'error': 'El trabajador ya tiene una asistencia registrada hoy',
                        'asistencia': AsistenciaSerializer(asistencia_existente).data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear asistencia
            asistencia = Asistencia()
            asistencia.trabajador = trabajador
            asistencia.proyecto = proyecto
            asistencia.marcar_entrada(
                hora=data.get('hora_entrada'),
                latitud=data.get('latitud'),
                longitud=data.get('longitud'),
                metodo=data.get('metodo_identificacion', 'qr'),
                dispositivo_id=data.get('dispositivo_id', ''),
                usuario=request.user
            )
            
            if data.get('observaciones'):
                asistencia.observaciones = data['observaciones']
                asistencia.save(update_fields=['observaciones'])
            
            return Response(
                {
                    'message': 'Entrada registrada exitosamente',
                    'asistencia': AsistenciaSerializer(asistencia).data
                },
                status=status.HTTP_201_CREATED
            )
        
        except Trabajador.DoesNotExist:
            return Response(
                {'error': 'Trabajador no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Proyecto.DoesNotExist:
            return Response(
                {'error': 'Proyecto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='check-out')
    def check_out(self, request):
        """
        Endpoint para marcar salida (check-out)
        
        POST /api/asistencias/check-out/
        Body: {
            "asistencia_id": 1,
            "hora_salida": "17:00:00",  // Opcional
            "latitud": -25.2637,  // Opcional
            "longitud": -57.5759,  // Opcional
            "observaciones": ""
        }
        """
        serializer = CheckOutSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            asistencia = Asistencia.objects.get(id=data['asistencia_id'])
            
            if asistencia.estado == 'cerrado':
                return Response(
                    {'error': 'Esta asistencia ya está cerrada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            asistencia.marcar_salida(
                hora=data.get('hora_salida'),
                latitud=data.get('latitud'),
                longitud=data.get('longitud'),
                usuario=request.user
            )
            
            if data.get('observaciones'):
                asistencia.observaciones = data['observaciones']
                asistencia.save(update_fields=['observaciones'])
            
            return Response(
                {
                    'message': 'Salida registrada exitosamente',
                    'asistencia': AsistenciaSerializer(asistencia).data
                },
                status=status.HTTP_200_OK
            )
        
        except Asistencia.DoesNotExist:
            return Response(
                {'error': 'Asistencia no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='asistencias-abiertas')
    def asistencias_abiertas(self, request):
        """
        Lista asistencias abiertas (sin check-out)
        GET /api/asistencias/asistencias-abiertas/
        """
        asistencias = self.get_queryset().filter(estado='abierto')
        serializer = AsistenciaListSerializer(
            asistencias,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='sincronizar')
    def sincronizar(self, request):
        """
        Sincronización batch desde app móvil offline
        
        POST /api/asistencias/sincronizar/
        Body: {
            "asistencias": [
                {
                    "trabajador_cedula": "1234567890",
                    "proyecto_id": 1,
                    "fecha": "2025-10-28",
                    "hora_entrada": "07:30:00",
                    "hora_salida": "17:00:00",
                    "latitud_entrada": -25.2637,
                    "longitud_entrada": -57.5759,
                    ...
                }
            ]
        }
        """
        serializer = SincronizarAsistenciasSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        asistencias_data = serializer.validated_data['asistencias']
        
        resultados = {
            'exitosas': 0,
            'fallidas': 0,
            'errores': []
        }
        
        for data in asistencias_data:
            try:
                trabajador = Trabajador.objects.get(
                    numero_cedula=data['trabajador_cedula'],
                    eliminado=False
                )
                proyecto = Proyecto.objects.get(id=data['proyecto_id'])
                
                # Verificar duplicados
                fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
                existe = Asistencia.objects.filter(
                    trabajador=trabajador,
                    fecha=fecha
                ).exists()
                
                if existe:
                    resultados['fallidas'] += 1
                    resultados['errores'].append(f"Asistencia duplicada para {trabajador.nombre_completo} en {fecha}")
                    continue
                
                # Crear asistencia
                asistencia = Asistencia.objects.create(
                    trabajador=trabajador,
                    proyecto=proyecto,
                    fecha=fecha,
                    hora_entrada=data.get('hora_entrada'),
                    hora_salida=data.get('hora_salida'),
                    latitud_entrada=data.get('latitud_entrada'),
                    longitud_entrada=data.get('longitud_entrada'),
                    latitud_salida=data.get('latitud_salida'),
                    longitud_salida=data.get('longitud_salida'),
                    metodo_identificacion=data.get('metodo_identificacion', 'qr'),
                    dispositivo_id=data.get('dispositivo_id', ''),
                    observaciones=data.get('observaciones', ''),
                    registrado_por=request.user,
                    estado='sincronizado',
                    sincronizado_en=timezone.now()
                )
                
                resultados['exitosas'] += 1
            
            except Exception as e:
                resultados['fallidas'] += 1
                resultados['errores'].append(str(e))
        
        return Response(resultados, status=status.HTTP_200_OK)
    