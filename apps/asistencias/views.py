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
    ResumenDiarioSerializer,
    ValidarAsistenciaSerializer,
    RechazarAsistenciaSerializer,
    CorregirAsistenciaSerializer,
    AsistenciaPendienteValidacionSerializer,
)

from .permissions import (
    PuedeValidarAsistencias,
    PuedeCorregirAsistencias,
    EsSupervisorDelProyecto,
)
from apps.trabajadores.models import Trabajador
from apps.proyectos.models import Proyecto

import csv


# ============================================
# VISTAS WEB
# ============================================

# ========================================
# VISTA: LISTA DE PENDIENTES
# ========================================

class AsistenciaValidarListView(LoginRequiredMixin, ListView):
    """
    Vista para listar asistencias pendientes de validación
    
    URL: /asistencias/validar/
    Template: templates/asistencias/validar_lista.html
    """
    model = Asistencia
    template_name = 'asistencias/validar_lista.html'
    context_object_name = 'asistencias'
    paginate_by = 50
    
    def get_queryset(self):
        """
        Obtiene asistencias pendientes de validación
        """
        # Filtro base: cerradas, no validadas, no eliminadas
        queryset = Asistencia.objects.filter(
            estado='cerrado',
            validado=False,
            eliminado=False
        ).select_related('trabajador', 'proyecto', 'registrado_por')
        
        # Si es supervisor, solo sus proyectos
        if self.request.user.es_supervisor() and not self.request.user.es_administrador():
            queryset = queryset.filter(proyecto__supervisor=self.request.user)
        
        # Filtros desde GET
        proyecto_id = self.request.GET.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        fecha_inicio = self.request.GET.get('fecha_inicio')
        if fecha_inicio:
            try:
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            except:
                pass
        
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_fin:
            try:
                queryset = queryset.filter(fecha__lte=fecha_fin)
            except:
                pass
        
        # Búsqueda por nombre de trabajador
        busqueda = self.request.GET.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(trabajador__nombre__icontains=busqueda) |
                Q(trabajador__apellido__icontains=busqueda) |
                Q(trabajador__numero_cedula__icontains=busqueda)
            )
        
        # Ordenar
        return queryset.order_by('-fecha', '-hora_entrada')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Proyectos para filtro
        if self.request.user.es_administrador():
            proyectos = Proyecto.objects.filter(activo=True, eliminado=False)
        else:
            proyectos = Proyecto.objects.filter(
                supervisor=self.request.user,
                activo=True,
                eliminado=False
            )
        context['proyectos'] = proyectos
        
        # Estadísticas
        queryset_base = self.get_queryset()
        
        context['estadisticas'] = {
            'total_pendientes': queryset_base.count(),
            'validadas_hoy': Asistencia.objects.filter(
                validado=True,
                validado_fecha__date=timezone.now().date()
            ).count(),
            'pendientes_hoy': queryset_base.filter(
                fecha=timezone.now().date()
            ).count(),
            'pendientes_ayer': queryset_base.filter(
                fecha=timezone.now().date() - timedelta(days=1)
            ).count(),
        }
        
        # Mantener filtros en el contexto
        context['filtros'] = {
            'proyecto': self.request.GET.get('proyecto', ''),
            'fecha_inicio': self.request.GET.get('fecha_inicio', ''),
            'fecha_fin': self.request.GET.get('fecha_fin', ''),
            'busqueda': self.request.GET.get('busqueda', ''),
        }
        
        return context


# ========================================
# VISTA: VALIDAR/RECHAZAR INDIVIDUAL
# ========================================

class AsistenciaValidarView(LoginRequiredMixin, View):
    """
    Vista para validar o rechazar una asistencia individual
    
    URL: /asistencias/<pk>/validar/
    Template: templates/asistencias/validar.html
    """
    template_name = 'asistencias/validar.html'
    
    def get(self, request, pk):
        """
        Muestra formulario de validación
        """
        asistencia = get_object_or_404(Asistencia, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not self._tiene_permiso(request.user, asistencia):
            messages.error(
                request,
                '❌ No tienes permisos para validar esta asistencia.'
            )
            return redirect('asistencias_validar_lista')
        
        # Verificar que puede ser validada
        if not asistencia.puede_ser_validada():
            messages.error(
                request,
                '❌ Esta asistencia no puede ser validada.'
            )
            return redirect('asistencias_validar_lista')
        
        context = {
            'asistencia': asistencia,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """
        Procesa validación o rechazo
        """
        asistencia = get_object_or_404(Asistencia, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not self._tiene_permiso(request.user, asistencia):
            messages.error(
                request,
                '❌ No tienes permisos para validar esta asistencia.'
            )
            return redirect('asistencias_validar_lista')
        
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            if accion == 'validar':
                asistencia.validar(
                    usuario=request.user,
                    observaciones=observaciones
                )
                messages.success(
                    request,
                    f'✅ Asistencia validada exitosamente para {asistencia.trabajador.nombre_completo}'
                )
            
            elif accion == 'rechazar':
                if not observaciones or observaciones.strip() == '':
                    messages.error(
                        request,
                        '❌ Debe proporcionar un motivo para rechazar la asistencia.'
                    )
                    return redirect('asistencia_validar', pk=pk)
                
                asistencia.rechazar(
                    usuario=request.user,
                    motivo=observaciones
                )
                messages.warning(
                    request,
                    f'⚠️ Asistencia rechazada para {asistencia.trabajador.nombre_completo}'
                )
            
            else:
                messages.error(request, '❌ Acción no válida.')
                return redirect('asistencia_validar', pk=pk)
            
            return redirect('asistencias_validar_lista')
        
        except ValueError as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('asistencia_validar', pk=pk)
        except Exception as e:
            messages.error(request, f'❌ Error inesperado: {str(e)}')
            return redirect('asistencia_validar', pk=pk)
    
    def _tiene_permiso(self, usuario, asistencia):
        """
        Verifica si el usuario tiene permiso para validar
        """
        if usuario.es_administrador():
            return True
        
        if usuario.es_supervisor():
            return asistencia.proyecto.supervisor == usuario
        
        return False


# ========================================
# VISTA: CORREGIR MARCACIONES
# ========================================

class AsistenciaCorregirView(LoginRequiredMixin, View):
    """
    Vista para corregir marcaciones erróneas
    
    URL: /asistencias/<pk>/corregir/
    Template: templates/asistencias/corregir.html
    """
    template_name = 'asistencias/corregir.html'
    
    def get(self, request, pk):
        """
        Muestra formulario de corrección
        """
        asistencia = get_object_or_404(Asistencia, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not self._tiene_permiso(request.user, asistencia):
            messages.error(
                request,
                '❌ No tienes permisos para corregir esta asistencia.'
            )
            return redirect('asistencias_validar_lista')
        
        context = {
            'asistencia': asistencia,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """
        Procesa corrección de marcaciones
        """
        asistencia = get_object_or_404(Asistencia, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not self._tiene_permiso(request.user, asistencia):
            messages.error(
                request,
                '❌ No tienes permisos para corregir esta asistencia.'
            )
            return redirect('asistencias_validar_lista')
        
        # Obtener datos del formulario
        nueva_hora_entrada_str = request.POST.get('nueva_hora_entrada')
        nueva_hora_salida_str = request.POST.get('nueva_hora_salida')
        motivo = request.POST.get('motivo_correccion', '')
        
        # Validar que hay motivo
        if not motivo or motivo.strip() == '':
            messages.error(
                request,
                '❌ Debe proporcionar un motivo para la corrección.'
            )
            return redirect('asistencia_corregir', pk=pk)
        
        try:
            # Convertir horas
            nueva_hora_entrada = None
            nueva_hora_salida = None
            
            if nueva_hora_entrada_str:
                nueva_hora_entrada = datetime.strptime(nueva_hora_entrada_str, '%H:%M').time()
            
            if nueva_hora_salida_str:
                nueva_hora_salida = datetime.strptime(nueva_hora_salida_str, '%H:%M').time()
            
            # Validar que al menos una hora fue proporcionada
            if not nueva_hora_entrada and not nueva_hora_salida:
                messages.error(
                    request,
                    '❌ Debe proporcionar al menos una hora para corregir.'
                )
                return redirect('asistencia_corregir', pk=pk)
            
            # Corregir
            asistencia.corregir(
                usuario=request.user,
                nueva_hora_entrada=nueva_hora_entrada,
                nueva_hora_salida=nueva_hora_salida,
                motivo=motivo
            )
            
            messages.success(
                request,
                f'✅ Marcación corregida exitosamente para {asistencia.trabajador.nombre_completo}'
            )
            return redirect('asistencias_validar_lista')
        
        except ValueError as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('asistencia_corregir', pk=pk)
        except Exception as e:
            messages.error(request, f'❌ Error inesperado: {str(e)}')
            return redirect('asistencia_corregir', pk=pk)
    
    def _tiene_permiso(self, usuario, asistencia):
        """
        Verifica si el usuario tiene permiso para corregir
        """
        if usuario.es_administrador():
            return True
        
        if usuario.es_supervisor():
            return asistencia.proyecto.supervisor == usuario
        
        return False


class AsistenciaListView(LoginRequiredMixin, ListView):
    model = Asistencia
    template_name = 'asistencias/lista.html'
    context_object_name = 'asistencias'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Asistencia.objects.filter(
            eliminado=False
        ).select_related(
            'trabajador',
            'proyecto',
            'registrado_por'
        ).order_by('-fecha', '-hora_entrada')
        
        # Filtro por proyecto
        proyecto_id = self.request.GET.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        # Filtro por fechas
        fecha_inicio = self.request.GET.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Búsqueda
        busqueda = self.request.GET.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(trabajador__nombre__icontains=busqueda) |
                Q(trabajador__apellido__icontains=busqueda) |
                Q(trabajador__numero_cedula__icontains=busqueda)
            )
        
        # Si es supervisor, solo sus proyectos
        if self.request.user.es_supervisor() and not self.request.user.es_administrador():
            queryset = queryset.filter(proyecto__supervisor=self.request.user)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Agregar contexto adicional para el template
        """
        context = super().get_context_data(**kwargs)
        
        # Proyectos para filtro
        if self.request.user.es_administrador():
            proyectos = Proyecto.objects.filter(activo=True, eliminado=False)
        else:
            proyectos = Proyecto.objects.filter(
                supervisor=self.request.user,
                activo=True,
                eliminado=False
            )
        context['proyectos'] = proyectos
        
        # Obtener asistencias del período filtrado
        asistencias_periodo = self.get_queryset()
        
        # Contar pendientes de validación
        pendientes_validacion = asistencias_periodo.filter(
            estado='cerrado',
            validado=False
        ).count()
        
        # ============================================
        # REVISADO 1: Renombrar 'resumen' a 'stats' y ajustar las claves
        # ============================================
        # La plantilla espera 'stats', no 'resumen'.
        # También espera claves como 'cerrados', 'abiertos', 'tarde'.
        context['stats'] = {
            'cerrados': asistencias_periodo.filter(estado='cerrado').count(),
            'abiertos': asistencias_periodo.filter(estado='abierto').count(),
            'horas_extras': asistencias_periodo.aggregate(total=Sum('horas_extras'))['total'] or 0,
            'tarde': asistencias_periodo.filter(llego_tarde=True).count(),
            'pendientes_validacion': pendientes_validacion,
        }
        
        # ============================================
        # REVISADO 2: Reemplazar el bucle manual por un .annotate()
        # ============================================
        # El bucle manual de Python era ineficiente y usaba claves incorrectas.
        # Este .annotate() hace una sola consulta y devuelve los datos
        # exactamente como la plantilla los espera (ej. 'proyecto__nombre', 'total').
        
        resumen_proyectos = asistencias_periodo.values(
            'proyecto', 
            'proyecto__nombre'
        ).annotate(
            total=Count('id'),
            validadas=Count('id', filter=Q(validado=True)),
            pendientes=Count('id', filter=Q(estado='cerrado', validado=False)),
            total_horas=Sum('horas_totales')
        ).order_by('proyecto__nombre')

        context['resumen_proyectos'] = resumen_proyectos
        
        # Mantener filtros en el contexto
        context['filtros'] = {
            'proyecto': self.request.GET.get('proyecto', ''),
            'fecha_inicio': self.request.GET.get('fecha_inicio', ''),
            'fecha_fin': self.request.GET.get('fecha_fin', ''),
            'estado': self.request.GET.get('estado', ''),
            'busqueda': self.request.GET.get('busqueda', ''),
        }
        
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
        proyectos = Proyecto.objects.filter(
            # activo=True,
            eliminado=False
        ).order_by('nombre')
        
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
            hoy = timezone.now().date()
            asistencia_existente = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=hoy
            ).first()
            
            if asistencia_existente:
                if asistencia_existente.estado == 'abierto':
                    messages.warning(
                        request,
                        f'⚠️ {trabajador.nombre_completo} ya tiene un turno abierto hoy. '
                        f'Debe cerrar el turno actual antes de marcar una nueva entrada.'
                    )
                    return redirect('asistencia_marcar_entrada')
                else:
                    messages.warning(
                        request,
                        f'⚠️ {trabajador.nombre_completo} ya tiene un turno cerrado registrado hoy.'
                    )
                    return redirect('asistencia_marcar_entrada')
            
            # Determinar hora de entrada
            if hora_entrada_str:
                hora_entrada = datetime.strptime(hora_entrada_str, '%H:%M').time()
            else:
                hora_entrada = timezone.now().time()
            
            # Crear asistencia
            asistencia = Asistencia.objects.create(
                trabajador=trabajador,
                proyecto=proyecto,
                fecha=hoy,
                puesto_laboral=trabajador.puesto_laboral,
                hora_entrada=hora_entrada,
                observaciones=observaciones,
                registrado_por=request.user,
                estado='abierto'
            )
            
            messages.success(
                request,
                f'✅ Entrada registrada exitosamente para {trabajador.nombre_completo}'
            )
            
            # Redirigir de vuelta si hay return_url
            return_url = request.GET.get('return_url')
            if return_url:
                return redirect(return_url)
            
            return redirect('asistencia_detalle', pk=asistencia.id)
        
        except Trabajador.DoesNotExist:
            messages.error(request, '❌ Trabajador no encontrado')
            return redirect('asistencia_marcar_entrada')
        
        except Proyecto.DoesNotExist:
            messages.error(request, '❌ Proyecto no encontrado')
            return redirect('asistencia_marcar_entrada')
        
        except Exception as e:
            messages.error(request, f'❌ Error al registrar entrada: {str(e)}')
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
        
        # --- NUEVA LÓGICA ---
        # Comprobamos si se puede editar y preparamos el contexto
        puede_editar = asistencia.puede_editar
        motivo_no_editable = None

        if not puede_editar:
            # Intentamos obtener el motivo desde el modelo
            if hasattr(asistencia, 'motivo_no_editable'):
                motivo_no_editable = asistencia.motivo_no_editable
            else:
                # Si no existe, usamos la lógica de días
                # (Asumiendo 2 días según tu modelo, si no, cambia el número)
                dias = (timezone.now().date() - asistencia.fecha).days
                if dias > 2: 
                     motivo_no_editable = f"Han pasado {dias} días. Solo se pueden editar asistencias de los últimos 2 días."
                elif hasattr(asistencia, 'eliminado') and asistencia.eliminado:
                     motivo_no_editable = "Esta asistencia ha sido eliminada."
                else:
                     motivo_no_editable = "La asistencia ya no se puede modificar por reglas del sistema."
        
        return render(request, 'asistencias/editar.html', {
            'asistencia': asistencia,
            'puede_editar': puede_editar, # <-- Pasamos la variable
            'motivo_no_editable': motivo_no_editable # <-- Pasamos el motivo
        })
    
    def post(self, request, pk):
        asistencia = get_object_or_404(Asistencia, pk=pk)
        
        # La validación en POST es crucial por seguridad
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
                asistencia.estado = 'cerrado' # Asegurarse de cerrar el turno
            else:
                asistencia.hora_salida = None # Permitir re-abrir el turno
                asistencia.estado = 'abierto'
            
            asistencia.observaciones = observaciones
            asistencia.editado_por = request.user
            
            # Si se re-abre el turno, resetear horas
            if not asistencia.hora_salida:
                asistencia.horas_normales = 0
                asistencia.horas_extras = 0
                asistencia.horas_totales = 0
                asistencia.salio_temprano = False
            
            asistencia.save() # Esto llamará a calcular_horas y verificar_llegada_tarde
            
            messages.success(request, '✅ Asistencia actualizada correctamente.')
            return redirect('asistencia_detalle', pk=pk)
        
        except Exception as e:
            messages.error(request, f'❌ Error al editar asistencia: {str(e)}')
            return redirect('asistencia_editar', pk=pk)

class AsistenciaReportesView(LoginRequiredMixin, TemplateView):
    """Vista para generar reportes de asistencias"""
    template_name = 'asistencias/reportes.html'
    
    def get(self, request, *args, **kwargs):
        # Obtener parámetros de filtro
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')
        proyecto_id = request.GET.get('proyecto')
        
        # Valores por defecto: mes actual
        if not fecha_inicio_str or not fecha_fin_str:
            hoy = timezone.now().date()
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        else:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                hoy = timezone.now().date()
                fecha_inicio = hoy.replace(day=1)
                fecha_fin = hoy

        # Filtrar asistencias
        asistencias = Asistencia.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('trabajador', 'proyecto')
        
        if proyecto_id:
            asistencias = asistencias.filter(proyecto_id=proyecto_id)
        
        # Estadísticas generales
        stats = asistencias.aggregate(
            total_asistencias=Count('id'),
            total_trabajadores=Count('trabajador', distinct=True),
            horas_normales_total=Sum('horas_normales'),
            horas_extras_total=Sum('horas_extras'),
            horas_nocturnas_total=Sum('horas_nocturnas'),
            horas_festivas_total=Sum('horas_festivas'),
            llegadas_tarde=Count('id', filter=Q(llego_tarde=True)),
            salidas_temprano=Count('id', filter=Q(salio_temprano=True))
        )
        
        # Limpiar agregados nulos
        stats = {k: v or 0 for k, v in stats.items()}
        
        # Resumen por trabajador
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
            total_horas_nocturnas=Sum('horas_nocturnas'),
            total_horas_festivas=Sum('horas_festivas'),
            total_horas=Sum('horas_totales'),
            llegadas_tarde=Count('id', filter=Q(llego_tarde=True)),
            salidas_temprano_count=Count('id', filter=Q(salio_temprano=True))
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
        proyectos = Proyecto.objects.filter(activo=True, eliminado=False)
        
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
        'Salió Temprano', # Añadido
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
            'Sí' if asistencia.salio_temprano else 'No', # Añadido
            asistencia.get_estado_display(),
            asistencia.observaciones
        ])
    
    return response

class AsistenciaAgregarNotaView(LoginRequiredMixin, View):
    """Vista para agregar nota a una asistencia"""
    
    def post(self, request, pk):
        asistencia = get_object_or_404(Asistencia, id=pk)
        nota = request.POST.get('nota', '').strip()
        
        if nota:
            fecha_hora = timezone.now().strftime('%Y-%m-%d %H:%M')
            usuario = request.user.get_full_name() or request.user.username
            
            nueva_observacion = f"[{fecha_hora}] {usuario}: {nota}"
            
            if asistencia.observaciones:
                asistencia.observaciones += f"\n{nueva_observacion}"
            else:
                asistencia.observaciones = nueva_observacion
            
            asistencia.editado_por = request.user
            asistencia.save()
            
            messages.success(request, '✅ Nota agregada exitosamente')
        else:
            messages.error(request, '❌ La nota no puede estar vacía')
        
        return redirect('asistencia_detalle', pk=pk)

class AsistenciaHistorialView(LoginRequiredMixin, ListView):
    """Vista de historial de asistencias de un trabajador"""
    model = Asistencia
    template_name = 'asistencias/historial.html'
    context_object_name = 'asistencias'
    paginate_by = 20
    
    def get_queryset(self):
        trabajador_id = self.kwargs.get('trabajador_id')
        queryset = Asistencia.objects.filter(
            trabajador_id=trabajador_id
        ).select_related(
            'trabajador', 'proyecto'
        ).order_by('-fecha', '-hora_entrada')
        
        # Filtros
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        proyecto = self.request.GET.get('proyecto')
        estado = self.request.GET.get('estado')
        
        # Rango de fechas por defecto: último mes
        if not fecha_inicio and not fecha_fin:
            hoy = timezone.now().date()
            fecha_inicio = hoy - timedelta(days=30)
            fecha_fin = hoy
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if proyecto:
            queryset = queryset.filter(proyecto_id=proyecto)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        trabajador_id = self.kwargs.get('trabajador_id')
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        
        context['trabajador'] = trabajador
        
        # Obtener filtros
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        # Valores por defecto
        if not fecha_inicio and not fecha_fin:
            hoy = timezone.now().date()
            fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        
        context['filtros'] = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'proyecto': self.request.GET.get('proyecto', ''),
            'estado': self.request.GET.get('estado', ''),
        }
        
        # Proyectos para filtro
        context['proyectos'] = Proyecto.objects.filter(activo=True, eliminado=False)
        
        # Resumen del período
        asistencias_periodo = self.get_queryset()
        
        # Contar llegadas tarde
        total_llegadas_tarde = asistencias_periodo.filter(llego_tarde=True).count()
        
        context['resumen'] = {
            'dias_trabajados': asistencias_periodo.filter(estado='cerrado').count(),
            'dias_ausentes': asistencias_periodo.filter(estado='abierto').count(),
            'horas_normales': asistencias_periodo.aggregate(
                total=Sum('horas_normales')
            )['total'] or 0,
            'horas_extras': asistencias_periodo.aggregate(
                total=Sum('horas_extras')
            )['total'] or 0,
            'minutos_tarde': total_llegadas_tarde,
        }
        
        # Última asistencia para validación de coordenadas
        context['ultima_asistencia'] = asistencias_periodo.first()
        
        return context
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
        elif self.action == 'check_in':
            return CheckInSerializer
        elif self.action == 'check_out':
            return CheckOutSerializer
        elif self.action == 'sincronizar':
            return SincronizarAsistenciasSerializer
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
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Buscar trabajador
            trabajador = Trabajador.objects.get(
                numero_cedula=data['trabajador_cedula'],
                eliminado=False,
                estado='activo' # Solo trabajadores activos pueden marcar
            )
            
            # Buscar proyecto
            proyecto = Proyecto.objects.get(id=data['proyecto_id'], eliminado=False)
            
            # Verificar si ya tiene asistencia hoy
            hoy = timezone.now().date()
            asistencia_existente = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=hoy
            ).first()
            
            if asistencia_existente:
                if asistencia_existente.estado == 'abierto':
                    return Response(
                        {
                            'error': 'El trabajador ya tiene un turno abierto hoy',
                            'asistencia': AsistenciaSerializer(asistencia_existente).data
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        {
                            'error': 'El trabajador ya tiene un turno cerrado hoy',
                            'asistencia': AsistenciaSerializer(asistencia_existente).data
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Hora de entrada
            hora_entrada = data.get('hora_entrada') or timezone.localtime().time()

            # Crear asistencia
            asistencia = Asistencia.objects.create(
                trabajador=trabajador,
                proyecto=proyecto,
                fecha=hoy,
                puesto_laboral=trabajador.puesto_laboral,
                hora_entrada=hora_entrada,
                latitud_entrada=data.get('latitud'),
                longitud_entrada=data.get('longitud'),
                metodo_identificacion=data.get('metodo_identificacion', 'qr'),
                dispositivo_id=data.get('dispositivo_id', ''),
                observaciones=data.get('observaciones', ''),
                registrado_por=request.user,
                estado='abierto'
            )
            
            # TODO: Validar geolocalización aquí si es necesario
            
            return Response(
                {
                    'message': 'Entrada registrada exitosamente',
                    'asistencia': AsistenciaSerializer(asistencia).data
                },
                status=status.HTTP_201_CREATED
            )
        
        except Trabajador.DoesNotExist:
            return Response(
                {'error': 'Trabajador no encontrado o inactivo'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Proyecto.DoesNotExist:
            return Response(
                {'error': 'Proyecto no encontrado o inactivo'},
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
        """
        serializer = self.get_serializer(data=request.data)
        
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
            
            hora_salida = data.get('hora_salida') or timezone.localtime().time()

            # Usar el método del modelo para cerrar el turno
            asistencia.cerrar_turno(hora_salida=hora_salida)
            
            # Actualizar campos de salida
            asistencia.latitud_salida=data.get('latitud')
            asistencia.longitud_salida=data.get('longitud')
            
            if data.get('observaciones'):
                if asistencia.observaciones:
                    asistencia.observaciones += f"\n[SALIDA]: {data['observaciones']}"
                else:
                    asistencia.observaciones = f"[SALIDA]: {data['observaciones']}"
            
            asistencia.editado_por = request.user
            asistencia.save()
            
            # TODO: Validar geolocalización de salida aquí
            
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
                status=status.HTTP_44_NOT_FOUND
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
        """
        serializer = self.get_serializer(data=request.data)
        
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
                
                fecha = data['fecha']
                
                # Usar update_or_create para manejar duplicados de sincronización
                asistencia, created = Asistencia.objects.update_or_create(
                    trabajador=trabajador,
                    fecha=fecha,
                    defaults={
                        'proyecto': proyecto,
                        'hora_entrada': data.get('hora_entrada'),
                        'hora_salida': data.get('hora_salida'),
                        'puesto_laboral': trabajador.puesto_laboral,
                        'latitud_entrada': data.get('latitud_entrada'),
                        'longitud_entrada': data.get('longitud_entrada'),
                        'latitud_salida': data.get('latitud_salida'),
                        'longitud_salida': data.get('longitud_salida'),
                        'metodo_identificacion': data.get('metodo_identificacion', 'qr'),
                        'dispositivo_id': data.get('dispositivo_id', ''),
                        'observaciones': data.get('observaciones', ''),
                        'registrado_por': request.user,
                        'editado_por': request.user,
                        'estado': 'cerrado' if data.get('hora_salida') else 'abierto',
                        'sincronizado_en': timezone.now()
                    }
                )
                
                # Recalcular horas (save() lo hace)
                asistencia.save()
                
                resultados['exitosas'] += 1
            
            except Exception as e:
                resultados['fallidas'] += 1
                resultados['errores'].append(f"Cédula {data.get('trabajador_cedula')}: {str(e)}")
        
        return Response(resultados, status=status.HTTP_200_OK)
    
    @action(
    detail=True,
    methods=['post'],
    url_path='validar',
    permission_classes=[PuedeValidarAsistencias, EsSupervisorDelProyecto]
    )
    def validar(self, request, pk=None):
        """
        Valida una asistencia
        
        POST /api/asistencias/{id}/validar/
        
        Body:
        {
            "observaciones": "Asistencia verificada y correcta"
        }
        
        Returns:
            200: Asistencia validada exitosamente
            400: Error en validación
            403: Sin permisos
            404: Asistencia no encontrada
        """
        asistencia = self.get_object()
        
        serializer = ValidarAsistenciaSerializer(
            data=request.data,
            context={'asistencia': asistencia}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validar usando el método del modelo
            asistencia.validar(
                usuario=request.user,
                observaciones=serializer.validated_data.get('observaciones', '')
            )
            
            # Serializar y retornar
            from .serializers import AsistenciaSerializer
            response_serializer = AsistenciaSerializer(asistencia)
            
            return Response({
                'message': 'Asistencia validada exitosamente',
                'asistencia': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error inesperado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(
        detail=True,
        methods=['post'],
        url_path='rechazar',
        permission_classes=[PuedeValidarAsistencias, EsSupervisorDelProyecto]
    )
    def rechazar(self, request, pk=None):
        """
        Rechaza una asistencia
        
        POST /api/asistencias/{id}/rechazar/
        
        Body:
        {
            "motivo": "Horario incorrecto, trabajador llegó más tarde"
        }
        
        Returns:
            200: Asistencia rechazada exitosamente
            400: Error en validación
            403: Sin permisos
            404: Asistencia no encontrada
        """
        asistencia = self.get_object()
        
        serializer = RechazarAsistenciaSerializer(
            data=request.data,
            context={'asistencia': asistencia}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Rechazar usando el método del modelo
            asistencia.rechazar(
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )
            
            # Serializar y retornar
            from .serializers import AsistenciaSerializer
            response_serializer = AsistenciaSerializer(asistencia)
            
            return Response({
                'message': 'Asistencia rechazada',
                'asistencia': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error inesperado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(
        detail=True,
        methods=['post'],
        url_path='corregir',
        permission_classes=[PuedeCorregirAsistencias, EsSupervisorDelProyecto]
    )
    def corregir(self, request, pk=None):
        """
        Corrige las marcaciones de una asistencia
        
        POST /api/asistencias/{id}/corregir/
        
        Body:
        {
            "nueva_hora_entrada": "08:15:00",
            "nueva_hora_salida": "17:30:00",
            "motivo_correccion": "El trabajador olvidó marcar salida, se corrige según reporte"
        }
        
        Returns:
            200: Asistencia corregida exitosamente
            400: Error en validación
            403: Sin permisos
            404: Asistencia no encontrada
        """
        asistencia = self.get_object()
        
        serializer = CorregirAsistenciaSerializer(
            data=request.data,
            context={'asistencia': asistencia}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Corregir usando el método del modelo
            asistencia.corregir(
                usuario=request.user,
                nueva_hora_entrada=serializer.validated_data.get('nueva_hora_entrada'),
                nueva_hora_salida=serializer.validated_data.get('nueva_hora_salida'),
                motivo=serializer.validated_data['motivo_correccion']
            )
            
            # Serializar y retornar
            from .serializers import AsistenciaSerializer
            response_serializer = AsistenciaSerializer(asistencia)
            
            return Response({
                'message': 'Asistencia corregida exitosamente',
                'asistencia': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error inesperado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(
        detail=False,
        methods=['get'],
        url_path='pendientes-validacion',
        permission_classes=[PuedeValidarAsistencias]
    )
    def pendientes_validacion(self, request):
        """
        Lista asistencias pendientes de validación
        
        GET /api/asistencias/pendientes-validacion/
        
        Query params:
            - proyecto: ID del proyecto (opcional)
            - fecha_inicio: Filtrar desde fecha (opcional, formato YYYY-MM-DD)
            - fecha_fin: Filtrar hasta fecha (opcional, formato YYYY-MM-DD)
        
        Returns:
            200: Lista de asistencias pendientes
        """
        # Filtro base: asistencias cerradas, no validadas, no eliminadas
        queryset = self.get_queryset().filter(
            estado='cerrado',
            validado=False,
            eliminado=False
        )
        
        # Si es supervisor, solo ver sus proyectos
        if request.user.es_supervisor() and not request.user.es_administrador():
            queryset = queryset.filter(proyecto__supervisor=request.user)
        
        # Filtros opcionales
        proyecto_id = request.query_params.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        fecha_inicio = request.query_params.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        fecha_fin = request.query_params.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Ordenar por fecha descendente
        queryset = queryset.order_by('-fecha', '-hora_entrada')
        
        # Serializar
        serializer = AsistenciaPendienteValidacionSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        
        # Estadísticas
        total_pendientes = queryset.count()
        validadas_hoy = self.get_queryset().filter(
            validado=True,
            validado_fecha__date=timezone.now().date()
        ).count()
        
        return Response({
            'count': total_pendientes,
            'validadas_hoy': validadas_hoy,
            'results': serializer.data
        }, status=status.HTTP_200_OK)


    @action(
        detail=False,
        methods=['post'],
        url_path='validar-multiple',
        permission_classes=[PuedeValidarAsistencias]
    )
    def validar_multiple(self, request):
        """
        Valida múltiples asistencias a la vez
        
        POST /api/asistencias/validar-multiple/
        
        Body:
        {
            "asistencias_ids": [1, 2, 3, 4, 5],
            "observaciones": "Validación masiva del día"
        }
        
        Returns:
            200: Resultado de validación masiva
        """
        asistencias_ids = request.data.get('asistencias_ids', [])
        observaciones = request.data.get('observaciones', '')
        
        if not asistencias_ids or not isinstance(asistencias_ids, list):
            return Response(
                {'error': 'Debe proporcionar una lista de IDs de asistencias'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener asistencias
        queryset = self.get_queryset().filter(
            id__in=asistencias_ids,
            estado='cerrado',
            validado=False,
            eliminado=False
        )
        
        # Si es supervisor, filtrar por sus proyectos
        if request.user.es_supervisor() and not request.user.es_administrador():
            queryset = queryset.filter(proyecto__supervisor=request.user)
        
        resultados = {
            'exitosas': [],
            'fallidas': [],
            'total_procesadas': 0,
            'total_exitosas': 0,
            'total_fallidas': 0
        }
        
        for asistencia in queryset:
            try:
                asistencia.validar(
                    usuario=request.user,
                    observaciones=observaciones
                )
                resultados['exitosas'].append(asistencia.id)
                resultados['total_exitosas'] += 1
            except Exception as e:
                resultados['fallidas'].append({
                    'id': asistencia.id,
                    'error': str(e)
                })
                resultados['total_fallidas'] += 1
            
            resultados['total_procesadas'] += 1
        
        return Response({
            'message': f'Procesadas {resultados["total_procesadas"]} asistencias',
            'resultados': resultados
        }, status=status.HTTP_200_OK)

    # ============================================
    # API TEMPORAL PARA PRUEBAS - ELIMINAR ASISTENCIAS
    # ============================================
    # 
    # AGREGAR EN: apps/asistencias/views.py (dentro de AsistenciaViewSet)
    #
    # ⚠️ IMPORTANTE: ELIMINAR DESPUÉS DE LAS PRUEBAS
    # ============================================

    @action(detail=False, methods=['delete', 'post'], url_path='limpiar-pruebas')
    def limpiar_pruebas(self, request):
        """
        🧪 ENDPOINT TEMPORAL PARA PRUEBAS - ELIMINAR DESPUÉS
        
        Elimina asistencias para poder repetir pruebas de check-in
        
        DELETE /api/asistencias/limpiar-pruebas/
        
        Body opciones:
        1. Eliminar por ID específico:
        {"asistencia_id": 123}
        
        2. Eliminar todas las de hoy de un trabajador:
        {"trabajador_cedula": "2812903031000Q"}
        
        3. Eliminar todas las de hoy:
        {"todas_hoy": true}
        
        4. Eliminar por proyecto hoy:
        {"proyecto_id": 2}
        """
        from django.utils import timezone
        
        hoy = timezone.now().date()
        
        # Opción 1: Por ID específico
        asistencia_id = request.data.get('asistencia_id')
        if asistencia_id:
            deleted, _ = Asistencia.objects.filter(id=asistencia_id).delete()
            return Response({
                'message': f'Asistencia {asistencia_id} eliminada',
                'eliminadas': deleted
            })
        
        # Opción 2: Por cédula del trabajador (solo hoy)
        trabajador_cedula = request.data.get('trabajador_cedula')
        if trabajador_cedula:
            deleted, _ = Asistencia.objects.filter(
                trabajador__numero_cedula=trabajador_cedula,
                fecha=hoy
            ).delete()
            return Response({
                'message': f'Asistencias de hoy eliminadas para cédula {trabajador_cedula}',
                'eliminadas': deleted
            })
        
        # Opción 3: Todas las de hoy
        todas_hoy = request.data.get('todas_hoy')
        if todas_hoy:
            deleted, _ = Asistencia.objects.filter(fecha=hoy).delete()
            return Response({
                'message': f'Todas las asistencias de hoy eliminadas',
                'eliminadas': deleted
            })
        
        # Opción 4: Por proyecto (solo hoy)
        proyecto_id = request.data.get('proyecto_id')
        if proyecto_id:
            deleted, _ = Asistencia.objects.filter(
                proyecto_id=proyecto_id,
                fecha=hoy
            ).delete()
            return Response({
                'message': f'Asistencias de hoy eliminadas para proyecto {proyecto_id}',
                'eliminadas': deleted
            })
        
        return Response({
            'error': 'Debe enviar: asistencia_id, trabajador_cedula, todas_hoy o proyecto_id',
            'ejemplos': {
                'por_id': {'asistencia_id': 123},
                'por_cedula': {'trabajador_cedula': '2812903031000Q'},
                'todas_hoy': {'todas_hoy': True},
                'por_proyecto': {'proyecto_id': 2}
            }
        }, status=400)
        