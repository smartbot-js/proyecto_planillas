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
from apps.admin_panel.permissions import PermissionRequiredMixin

import csv
import re

import logging
logger = logging.getLogger('registro_asistencias')

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
        
        # Filtrar por proyectos permitidos según rol
        if not self.request.user.es_administrador():
            proyectos_permitidos = self.request.user.get_proyectos_permitidos()
            queryset = queryset.filter(proyecto__in=proyectos_permitidos)
        
        # Filtros desde GET
        proyecto_id = self.request.GET.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        # Filtro por fechas (con validación)
        fecha_inicio = self.request.GET.get('fecha_inicio')
        if fecha_inicio:
            try:
                fecha_parsed = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                if fecha_parsed.year > 9999 or fecha_parsed.year < 1900:
                    raise ValueError('Año fuera de rango')
                queryset = queryset.filter(fecha__gte=fecha_parsed)
            except (ValueError, TypeError):
                messages.warning(self.request, f'⚠️ Fecha inicio inválida: "{fecha_inicio}". Se ignoró este filtro.')
        
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_fin:
            try:
                fecha_parsed = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                if fecha_parsed.year > 9999 or fecha_parsed.year < 1900:
                    raise ValueError('Año fuera de rango')
                queryset = queryset.filter(fecha__lte=fecha_parsed)
            except (ValueError, TypeError):
                messages.warning(self.request, f'⚠️ Fecha fin inválida: "{fecha_fin}". Se ignoró este filtro.')
        
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
        
        # Proyectos para filtro (según permisos del usuario)
        context['proyectos'] = self.request.user.get_proyectos_permitidos()
        
        # Estadísticas
        queryset_base = self.get_queryset()
        
        context['estadisticas'] = {
            'total_pendientes': queryset_base.count(),
            'validadas_hoy': Asistencia.objects.filter(
                validado=True,
                validado_fecha__date=timezone.localdate()
            ).count(),
            'pendientes_hoy': queryset_base.filter(
                fecha=timezone.localdate()
            ).count(),
            'pendientes_ayer': queryset_base.filter(
                fecha=timezone.localdate() - timedelta(days=1)
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

class AsistenciaValidarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Vista para validar o rechazar una asistencia individual
    
    URL: /asistencias/<pk>/validar/
    Template: templates/asistencias/validar.html
    """
    permission_modulo = 'asistencias'
    permission_accion = 'validar'
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
        
        # Verificar que tiene permiso de validar en su rol
        if not usuario.tiene_permiso('asistencias', 'validar'):
            return False
        
        # Verificar que tiene acceso al proyecto de la asistencia
        return usuario.puede_ver_proyecto(asistencia.proyecto)

class AsistenciaValidarTodasView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Validar todas las asistencias pendientes de golpe"""
    permission_modulo = 'asistencias'
    permission_accion = 'validar'

    def post(self, request):
        # Filtro base: cerradas, no validadas, no eliminadas
        queryset = Asistencia.objects.filter(
            estado='cerrado',
            validado=False,
            eliminado=False
        )

        # Filtrar por proyectos permitidos según rol
        if not request.user.es_administrador():
            proyectos_permitidos = request.user.get_proyectos_permitidos()
            queryset = queryset.filter(proyecto__in=proyectos_permitidos)

        # Aplicar mismos filtros del GET (si vienen del form)
        proyecto_id = request.POST.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)

        fecha_inicio = request.POST.get('fecha_inicio')
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)

        fecha_fin = request.POST.get('fecha_fin')
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        total = queryset.count()

        if total == 0:
            messages.info(request, 'No hay asistencias pendientes de validación.')
            return redirect('asistencias_validar_lista')

        # Validar masivamente
        queryset.update(
            validado=True,
            validado_por=request.user,
            validado_fecha=timezone.now(),
            observaciones_validacion='Validada masivamente'
        )

        messages.success(request, f'✅ {total} asistencias validadas exitosamente.')
        return redirect('asistencias_validar_lista')
        
# ========================================
# VISTA: CORREGIR MARCACIONES
# ========================================

class AsistenciaCorregirView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Vista para corregir marcaciones erróneas
    
    URL: /asistencias/<pk>/corregir/
    Template: templates/asistencias/corregir.html
    """
    permission_modulo = 'asistencias'
    permission_accion = 'corregir'
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
            'puede_editar': asistencia.puede_editar,
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
        
        # Verificar que tiene permiso de corregir en su rol
        if not usuario.tiene_permiso('asistencias', 'corregir'):
            return False
        
        # Verificar que tiene acceso al proyecto de la asistencia
        return usuario.puede_ver_proyecto(asistencia.proyecto)


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
        
        # Filtro por fechas (con validación, mensaje solo una vez)
        fecha_inicio = self.request.GET.get('fecha_inicio')
        if fecha_inicio:
            try:
                fecha_parsed = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                if fecha_parsed.year > 9999 or fecha_parsed.year < 1900:
                    raise ValueError('Año fuera de rango')
                queryset = queryset.filter(fecha__gte=fecha_parsed)
            except (ValueError, TypeError):
                if not getattr(self, '_fecha_inicio_warned', False):
                    messages.warning(self.request, f'⚠️ Fecha inicio inválida: "{fecha_inicio}". Se ignoró este filtro.')
                    self._fecha_inicio_warned = True
        
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_fin:
            try:
                fecha_parsed = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                if fecha_parsed.year > 9999 or fecha_parsed.year < 1900:
                    raise ValueError('Año fuera de rango')
                queryset = queryset.filter(fecha__lte=fecha_parsed)
            except (ValueError, TypeError):
                if not getattr(self, '_fecha_fin_warned', False):
                    messages.warning(self.request, f'⚠️ Fecha fin inválida: "{fecha_fin}". Se ignoró este filtro.')
                    self._fecha_fin_warned = True
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
        # Filtrar por proyectos permitidos según rol del usuario
        if not self.request.user.es_administrador():
            proyectos_permitidos = self.request.user.get_proyectos_permitidos()
            queryset = queryset.filter(proyecto__in=proyectos_permitidos)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Agregar contexto adicional para el template
        """
        context = super().get_context_data(**kwargs)
        
        # Proyectos para filtro (según permisos del usuario)
        context['proyectos'] = self.request.user.get_proyectos_permitidos()
        
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


class AsistenciaMarcarEntradaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para marcar entrada manualmente"""
    permission_modulo = 'asistencias'
    permission_accion = 'crear'

    def get(self, request):
        if request.user.es_administrador():
            trabajadores = Trabajador.objects.filter(
                eliminado=False,
                estado='activo'
            ).order_by('nombre', 'apellido')
        else:
            proyectos_permitidos = request.user.get_proyectos_permitidos()
            trabajadores = Trabajador.objects.filter(
                eliminado=False,
                estado='activo',
                proyecto_asignado__in=proyectos_permitidos
            ).order_by('nombre', 'apellido')
        
        proyectos = request.user.get_proyectos_permitidos().order_by('nombre')
        
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
            
            # Verificar si tiene alguna asistencia abierta (sin cerrar), sin importar el día
            asistencia_abierta = Asistencia.objects.filter(
                trabajador=trabajador,
                estado='abierto',
                eliminado=False
            ).order_by('-fecha').first()
            
            if asistencia_abierta:
                messages.warning(
                    request,
                    f'⚠️ {trabajador.nombre_completo} tiene un turno abierto del '
                    f'{asistencia_abierta.fecha.strftime("%d/%m/%Y")} que no ha sido cerrado. '
                    f'Debe cerrar ese turno antes de registrar una nueva entrada.'
                )
                return redirect('asistencia_marcar_entrada')
            
            # Verificar si ya tiene asistencia cerrada hoy (evitar duplicados del mismo día)
            hoy = timezone.localdate()
            asistencia_hoy = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=hoy,
                eliminado=False
            ).first()
            
            if asistencia_hoy:
                messages.warning(
                    request,
                    f'⚠️ {trabajador.nombre_completo} ya tiene una asistencia registrada hoy.'
                )
                return redirect('asistencia_marcar_entrada')
            
            # Determinar hora de entrada
            if hora_entrada_str:
                hora_entrada = datetime.strptime(hora_entrada_str, '%H:%M').time()
            else:
                hora_entrada = timezone.localtime().time()
            
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
        
class AsistenciaCerrarTurnoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para cerrar el turno de un trabajador"""
    permission_modulo = 'asistencias'
    permission_accion = 'crear'
    
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
                hora_salida = timezone.localtime().time()
            
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

class AsistenciaEditarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para editar asistencia existente"""
    permission_modulo = 'asistencias'
    permission_accion = 'editar'

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
                dias = (timezone.localdate() - asistencia.fecha).days
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
            hoy = timezone.localdate()
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        else:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                hoy = timezone.localdate()
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
            hoy = timezone.localdate()
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
            hoy = timezone.localdate()
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
        print(f"DATA CHECK-IN: {request.data}")
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(
                f"Fallo en check-in | Datos recibidos: {request.data} | Errores: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Buscar trabajador
            # Buscar trabajador (acepta cédula con/sin guiones)
            from apps.trabajadores.utils import buscar_trabajador_por_cedula
            # Normalizar cédula entrante

            # Buscar trabajador por ID o por cédula
            trabajador = None
            trabajador_id = data.get('trabajador_id')
            trabajador_cedula = data.get('trabajador_cedula')
            
            if trabajador_id:
                try:
                    trabajador = Trabajador.objects.get(id=trabajador_id, eliminado=False)
                except Trabajador.DoesNotExist:
                    trabajador = None
            
            if not trabajador and trabajador_cedula:
                trabajador_cedula = re.sub(r'[^a-zA-Z0-9]', '', trabajador_cedula).upper()
                trabajador = buscar_trabajador_por_cedula(trabajador_cedula)
            
            if not trabajador:
                raise Trabajador.DoesNotExist
            
            if trabajador.estado != 'activo':
                return Response(
                    {'error': 'El trabajador no está activo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Buscar proyecto
            proyecto = Proyecto.objects.get(id=data['proyecto_id'], eliminado=False)
            
            # Parsear fecha del dispositivo para verificación
            hoy = timezone.localdate()
            fecha_registro = hoy
            
            fecha_app_str = data.get('fecha_app')
            if fecha_app_str:
                try:
                    from datetime import datetime as dt
                    fecha_app_dt = dt.strptime(fecha_app_str.strip(), '%Y-%m-%d %H:%M')
                    fecha_registro = fecha_app_dt.date()
                except (ValueError, AttributeError):
                    pass
            
            # Verificar si tiene un turno abierto (de cualquier fecha)
            asistencia_abierta = Asistencia.objects.filter(
                trabajador=trabajador,
                estado='abierto',
                eliminado=False
            ).first()
            
            if asistencia_abierta:
                return Response(
                    {
                        'error': f'El trabajador tiene una entrada abierta desde {asistencia_abierta.fecha.strftime("%d/%m/%Y")} a las {asistencia_abierta.hora_entrada.strftime("%I:%M %p")}. Debe cerrarla antes de registrar una nueva.',
                        'asistencia': AsistenciaSerializer(asistencia_abierta).data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar si ya tiene asistencia cerrada hoy
            asistencia_hoy = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=fecha_registro,
                eliminado=False
            ).exclude(estado='abierto').first()
            
            if asistencia_hoy:
                return Response(
                    {
                        'error': 'El trabajador ya tiene un turno cerrado hoy',
                        'asistencia': AsistenciaSerializer(asistencia_hoy).data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parsear fecha y hora del dispositivo
            fecha_registro = hoy
            hora_entrada = data.get('hora_entrada') or timezone.localtime().time()
            
            fecha_app_str = data.get('fecha_app')
            if fecha_app_str:
                try:
                    from datetime import datetime as dt
                    fecha_app_dt = dt.strptime(fecha_app_str.strip(), '%Y-%m-%d %H:%M')
                    fecha_registro = fecha_app_dt.date()
                    hora_entrada = fecha_app_dt.time()
                except (ValueError, AttributeError):
                    pass  # Si falla el parseo, usar valores del servidor

            # Crear asistencia
            asistencia = Asistencia.objects.create(
                trabajador=trabajador,
                proyecto=proyecto,
                fecha=fecha_registro,
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
        print(f"BODY CHECK-OUT: {request.data}")
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(
                f"Fallo en check-out | Datos recibidos: {request.data} | Errores: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            asistencia = None
            
            # Opción 1: buscar por asistencia_id directo
            if data.get('asistencia_id'):
                asistencia = Asistencia.objects.get(id=data['asistencia_id'])
            else:
                # Opción 2: buscar asistencia abierta por trabajador_id o cédula
                import re
                trabajador = None
                
                if data.get('trabajador_id'):
                    try:
                        trabajador = Trabajador.objects.get(id=data['trabajador_id'], eliminado=False)
                    except Trabajador.DoesNotExist:
                        pass
                
                if not trabajador and data.get('trabajador_cedula'):
                    from apps.trabajadores.utils import buscar_trabajador_por_cedula
                    cedula = re.sub(r'[^a-zA-Z0-9]', '', data['trabajador_cedula']).upper()
                    trabajador = buscar_trabajador_por_cedula(cedula)
                
                if not trabajador:
                    return Response(
                        {'error': 'No se encontró al trabajador'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                asistencia = Asistencia.objects.filter(
                    trabajador=trabajador,
                    estado='abierto',
                    eliminado=False
                ).order_by('-fecha').first()
                
                if not asistencia:
                    return Response(
                        {'error': 'No existe registro de entrada abierto para este trabajador'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if asistencia.estado == 'cerrado':
                return Response(
                    {'error': 'Esta asistencia ya está cerrada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            hora_salida = data.get('hora_salida') or timezone.localtime().time()
            
            # Parsear fecha/hora del dispositivo
            fecha_app_str = data.get('fecha_app')
            if fecha_app_str:
                try:
                    from datetime import datetime as dt
                    fecha_app_dt = dt.strptime(fecha_app_str.strip(), '%Y-%m-%d %H:%M')
                    hora_salida = fecha_app_dt.time()
                except (ValueError, AttributeError):
                    pass

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
        
        - Entrada y salida se procesan por separado
        - Si ya existe entrada para trabajador/fecha → responde "ya_sincronizado"
        - Si ya existe salida → responde "ya_sincronizado"
        - No modifica registros existentes
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        asistencias_data = serializer.validated_data['asistencias']
        
        resultados = {
            'sincronizadas': 0,
            'ya_sincronizadas': 0,
            'errores': 0,
            'resultados': []
        }
        
        # Mapa para vincular temp_id con asistencia creada en este batch
        temp_id_map = {}
        
        # Contador para asignar temp_id a entradas que no lo traen
        entrada_index = 0
        
        # Procesar cada registro
        for data in asistencias_data:
            tipo = data.get('tipo')
            temp_id = data.get('asistencia_temp_id')
            
            if tipo == 'entrada':
                entrada_index += 1
                
                try:
                    trabajador = Trabajador.objects.get(
                        numero_cedula=data['trabajador_cedula'],
                        eliminado=False
                    )
                    proyecto = Proyecto.objects.get(
                        id=data['proyecto_id'],
                        eliminado=False
                    )
                    fecha = data['fecha']
                    
                    # Verificar si ya existe entrada para este trabajador/fecha
                    asistencia_existente = Asistencia.objects.filter(
                        trabajador=trabajador,
                        fecha=fecha
                    ).first()
                    
                    if asistencia_existente:
                        # Ya existe - no modificar
                        resultados['ya_sincronizadas'] += 1
                        resultados['resultados'].append({
                            'temp_id': temp_id,
                            'asistencia_id': asistencia_existente.id,
                            'estado': 'ya_sincronizado',
                            'mensaje': 'Entrada ya registrada anteriormente'
                        })
                        # Guardar en mapa por si viene salida
                        temp_id_map[entrada_index] = asistencia_existente
                        if temp_id:
                            temp_id_map[temp_id] = asistencia_existente
                    else:
                        # Crear nueva entrada
                        asistencia = Asistencia.objects.create(
                            trabajador=trabajador,
                            proyecto=proyecto,
                            fecha=fecha,
                            puesto_laboral=trabajador.puesto_laboral,
                            hora_entrada=data.get('hora_entrada'),
                            latitud_entrada=data.get('latitud_entrada'),
                            longitud_entrada=data.get('longitud_entrada'),
                            metodo_identificacion=data.get('metodo_identificacion', 'qr'),
                            dispositivo_id=data.get('dispositivo_id', ''),
                            observaciones=data.get('observaciones', ''),
                            registrado_por=request.user,
                            estado='abierto',
                            sincronizado_en=timezone.now()
                        )
                        
                        resultados['sincronizadas'] += 1
                        resultados['resultados'].append({
                            'temp_id': temp_id,
                            'asistencia_id': asistencia.id,
                            'estado': 'exitoso',
                            'mensaje': 'Entrada registrada'
                        })
                        # Guardar en mapa
                        temp_id_map[entrada_index] = asistencia
                        if temp_id:
                            temp_id_map[temp_id] = asistencia
                
                except Trabajador.DoesNotExist:
                    resultados['errores'] += 1
                    resultados['resultados'].append({
                        'temp_id': temp_id,
                        'asistencia_id': None,
                        'estado': 'error',
                        'mensaje': f"Trabajador no encontrado: {data.get('trabajador_cedula')}"
                    })
                except Proyecto.DoesNotExist:
                    resultados['errores'] += 1
                    resultados['resultados'].append({
                        'temp_id': temp_id,
                        'asistencia_id': None,
                        'estado': 'error',
                        'mensaje': f"Proyecto no encontrado: {data.get('proyecto_id')}"
                    })
                except Exception as e:
                    resultados['errores'] += 1
                    resultados['resultados'].append({
                        'temp_id': temp_id,
                        'asistencia_id': None,
                        'estado': 'error',
                        'mensaje': str(e)
                    })
            
            elif tipo == 'salida':
                try:
                    # Buscar asistencia por temp_id
                    asistencia = temp_id_map.get(temp_id)
                    
                    if not asistencia:
                        resultados['errores'] += 1
                        resultados['resultados'].append({
                            'temp_id': temp_id,
                            'asistencia_id': None,
                            'estado': 'error',
                            'mensaje': f'No se encontró entrada con temp_id={temp_id}'
                        })
                        continue
                    
                    # Verificar si ya tiene salida
                    if asistencia.hora_salida:
                        resultados['ya_sincronizadas'] += 1
                        resultados['resultados'].append({
                            'temp_id': temp_id,
                            'asistencia_id': asistencia.id,
                            'estado': 'ya_sincronizado',
                            'mensaje': 'Salida ya registrada anteriormente'
                        })
                        continue
                    
                    # Registrar salida
                    asistencia.hora_salida = data.get('hora_salida')
                    asistencia.latitud_salida = data.get('latitud_salida')
                    asistencia.longitud_salida = data.get('longitud_salida')
                    asistencia.estado = 'cerrado'
                    asistencia.editado_por = request.user
                    asistencia.sincronizado_en = timezone.now()
                    
                    if data.get('observaciones'):
                        if asistencia.observaciones:
                            asistencia.observaciones += f"\n[SALIDA]: {data['observaciones']}"
                        else:
                            asistencia.observaciones = f"[SALIDA]: {data['observaciones']}"
                    
                    asistencia.save()
                    
                    resultados['sincronizadas'] += 1
                    resultados['resultados'].append({
                        'temp_id': temp_id,
                        'asistencia_id': asistencia.id,
                        'estado': 'exitoso',
                        'mensaje': 'Salida registrada'
                    })
                
                except Exception as e:
                    resultados['errores'] += 1
                    resultados['resultados'].append({
                        'temp_id': temp_id,
                        'asistencia_id': None,
                        'estado': 'error',
                        'mensaje': str(e)
                    })
        
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
            validado_fecha__date=timezone.localdate()
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
    @action(detail=False, methods=['get'], url_path='resumen-hoy')
    def resumen_hoy(self, request):
        """
        Resumen de asistencias del día actual por proyecto asignado del usuario.
        
        GET /api/asistencias/resumen-hoy/
        GET /api/asistencias/resumen-hoy/?proyecto_id=5
        
        Response:
        {
            "fecha": "2026-04-08",
            "proyectos": [
                {
                    "proyecto_id": 5,
                    "proyecto_nombre": "Remodelación Casa Monserrat",
                    "total_trabajadores": 10,
                    "entradas": 7,
                    "salidas": 5,
                    "pendientes": 2,
                    "ausentes": 3
                }
            ],
            "totales": {
                "total_trabajadores": 10,
                "entradas": 7,
                "salidas": 5,
                "pendientes": 2,
                "ausentes": 3
            }
        }
        """
        from apps.proyectos.models import Proyecto
        from apps.trabajadores.models import Trabajador
        
        hoy = timezone.localdate()
        user = request.user
        
        # Obtener proyectos del usuario
        proyecto_id = request.query_params.get('proyecto_id')
        if proyecto_id:
            proyectos = Proyecto.objects.filter(pk=proyecto_id, eliminado=False)
        else:
            proyectos = user.get_proyectos_permitidos()
        
        resultado_proyectos = []
        totales = {
            'total_trabajadores': 0,
            'entradas': 0,
            'salidas': 0,
            'pendientes': 0,
            'ausentes': 0,
        }
        
        for proyecto in proyectos:
            # Total de trabajadores activos asignados al proyecto
            total_trabajadores = Trabajador.objects.filter(
                proyecto_asignado=proyecto,
                eliminado=False,
                estado='activo'
            ).count()
            
            # Asistencias de hoy en este proyecto
            asistencias_hoy = Asistencia.objects.filter(
                proyecto=proyecto,
                fecha=hoy,
                eliminado=False
            )
            
            # Entradas = todos los que marcaron entrada hoy
            entradas = asistencias_hoy.count()
            
            # Salidas = los que ya cerraron turno (tienen hora_salida)
            salidas = asistencias_hoy.filter(estado='cerrado').count()
            
            # Pendientes = marcaron entrada pero no salida
            pendientes = asistencias_hoy.filter(estado='abierto').count()
            
            # Ausentes = trabajadores asignados que no marcaron entrada
            ausentes = total_trabajadores - entradas
            if ausentes < 0:
                ausentes = 0
            
            proyecto_data = {
                'proyecto_id': proyecto.id,
                'proyecto_nombre': proyecto.nombre,
                'total_trabajadores': total_trabajadores,
                'entradas': entradas,
                'salidas': salidas,
                'pendientes': pendientes,
                'ausentes': ausentes,
            }
            resultado_proyectos.append(proyecto_data)
            
            # Acumular totales
            totales['total_trabajadores'] += total_trabajadores
            totales['entradas'] += entradas
            totales['salidas'] += salidas
            totales['pendientes'] += pendientes
            totales['ausentes'] += ausentes
        
        return Response({
            'fecha': hoy.strftime('%Y-%m-%d'),
            'proyectos': resultado_proyectos,
            'totales': totales,
        }, status=status.HTTP_200_OK)

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
        
        hoy = timezone.localdate()
        
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

class AsistenciaJustificadaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Vista para registrar asistencia justificada de un día pasado.
    Permite ingresar fecha, hora entrada y hora salida.
    La asistencia se crea directamente en estado 'cerrado'.
    """
    permission_modulo = 'asistencias'
    permission_accion = 'crear'
    template_name = 'asistencias/registrar_justificada.html'

    def get(self, request):
        if request.user.es_administrador():
            trabajadores = Trabajador.objects.filter(
                eliminado=False,
                estado='activo'
            ).order_by('nombre', 'apellido')
        else:
            proyectos_permitidos = request.user.get_proyectos_permitidos()
            trabajadores = Trabajador.objects.filter(
                eliminado=False,
                estado='activo',
                proyecto_asignado__in=proyectos_permitidos
            ).order_by('nombre', 'apellido')

        proyectos = request.user.get_proyectos_permitidos().order_by('nombre')

        return render(request, self.template_name, {
            'trabajadores': trabajadores,
            'proyectos': proyectos,
        })

    def post(self, request):
        try:
            trabajador_id = request.POST.get('trabajador_id')
            proyecto_id = request.POST.get('proyecto_id')
            fecha_str = request.POST.get('fecha')
            hora_entrada_str = request.POST.get('hora_entrada')
            hora_salida_str = request.POST.get('hora_salida')
            justificacion = request.POST.get('justificacion', '').strip()

            # Validaciones básicas
            if not all([trabajador_id, proyecto_id, fecha_str, hora_entrada_str, hora_salida_str]):
                messages.error(request, '❌ Todos los campos son obligatorios.')
                return redirect('asistencia_justificada')

            if not justificacion:
                messages.error(request, '❌ Debe proporcionar una justificación.')
                return redirect('asistencia_justificada')

            trabajador = Trabajador.objects.get(id=trabajador_id, eliminado=False)
            
            # Usar proyecto asignado del trabajador, o el enviado por formulario como fallback
            if trabajador.proyecto_asignado:
                proyecto = trabajador.proyecto_asignado
            elif proyecto_id:
                proyecto = Proyecto.objects.get(id=proyecto_id, eliminado=False)
            else:
                messages.error(request, '❌ El trabajador no tiene proyecto asignado.')
                return redirect('asistencia_justificada')

            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_entrada = datetime.strptime(hora_entrada_str, '%H:%M').time()
            hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()

            # No permitir fecha futura
            hoy = timezone.localdate()
            if fecha > hoy:
                messages.error(request, '❌ No se puede registrar asistencia para una fecha futura.')
                return redirect('asistencia_justificada')

            # Verificar que no exista asistencia ese día
            asistencia_existente = Asistencia.objects.filter(
                trabajador=trabajador,
                fecha=fecha,
                eliminado=False
            ).first()

            if asistencia_existente:
                messages.warning(
                    request,
                    f'⚠️ {trabajador.nombre_completo} ya tiene una asistencia registrada el {fecha.strftime("%d/%m/%Y")}.'
                )
                return redirect('asistencia_justificada')

            # Validar que hora salida sea después de hora entrada
            if hora_salida <= hora_entrada:
                messages.error(request, '❌ La hora de salida debe ser posterior a la hora de entrada.')
                return redirect('asistencia_justificada')

            # Crear asistencia ya cerrada
            asistencia = Asistencia.objects.create(
                trabajador=trabajador,
                proyecto=proyecto,
                fecha=fecha,
                puesto_laboral=trabajador.puesto_laboral,
                hora_entrada=hora_entrada,
                hora_salida=hora_salida,
                salario_dia=trabajador.salario_normal or Decimal('0.00'),
                tarifa_hora_extra=trabajador.tarifa_hora_extra or Decimal('0.00'),
                metodo_identificacion='manual',
                observaciones=f'[JUSTIFICADA] {justificacion}\nRegistrada por: {request.user.nombre_completo}',
                registrado_por=request.user,
                estado='cerrado',
            )

            messages.success(
                request,
                f'✅ Asistencia justificada registrada para {trabajador.nombre_completo} '
                f'el {fecha.strftime("%d/%m/%Y")} ({asistencia.horas_normales}h normales, '
                f'{asistencia.horas_extras}h extras).'
            )
            return redirect('asistencia_detalle', pk=asistencia.id)

        except Trabajador.DoesNotExist:
            messages.error(request, '❌ Trabajador no encontrado.')
            return redirect('asistencia_justificada')
        except Proyecto.DoesNotExist:
            messages.error(request, '❌ Proyecto no encontrado.')
            return redirect('asistencia_justificada')
        except ValueError as e:
            messages.error(request, f'❌ Formato de fecha u hora inválido: {str(e)}')
            return redirect('asistencia_justificada')
        except Exception as e:
            messages.error(request, f'❌ Error al registrar: {str(e)}')
            return redirect('asistencia_justificada')
