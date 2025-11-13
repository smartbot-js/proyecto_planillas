"""
Vistas del módulo de planillas
apps/planillas/views.py
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import traceback


from .models import Planilla, DetallePlanilla, TipoCambio, DiaFeriado
from .utils import (
    generar_planilla_desde_asistencias,
    validar_periodo_planilla,
    obtener_resumen_asistencias
)
from apps.proyectos.models import Proyecto
from apps.usuarios.models import Usuario
from apps.asistencias.models import Asistencia


class PlanillaListView(LoginRequiredMixin, ListView):
    """Vista para listar todas las planillas"""
    model = Planilla
    template_name = 'planillas/lista.html'
    context_object_name = 'planillas'
    paginate_by = 12
    
    def get_queryset(self):
        """Retorna el queryset filtrado de planillas (excluye eliminadas)"""
        queryset = Planilla.objects.filter(
            eliminado=False
        ).select_related(
            'proyecto',
            'generada_por',
            'aprobada_gerente_por',
            'aprobada_contador_por'
        ).order_by('-fecha_generacion')
        
        # Filtro de búsqueda por código
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(proyecto__nombre__icontains=search) |
                Q(observaciones__icontains=search)
            )
        
        # Filtro por proyecto
        proyecto_id = self.request.GET.get('proyecto')
        if proyecto_id and proyecto_id != 'todos':
            queryset = queryset.filter(proyecto_id=proyecto_id)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado and estado != 'todos':
            queryset = queryset.filter(estado=estado)
        
        # Filtro por rango de fechas
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if fecha_desde:
            queryset = queryset.filter(periodo_inicio__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(periodo_fin__lte=fecha_hasta)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Agrega datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        
        # Queryset base para estadísticas (sin filtros de usuario)
        base_queryset = Planilla.objects.filter(eliminado=False)
        
        # Estadísticas generales
        context['total_planillas'] = base_queryset.count()
        context['planillas_borrador'] = base_queryset.filter(estado='borrador').count()
        context['planillas_aprobadas_gerente'] = base_queryset.filter(estado='aprobada_gerente').count()
        context['planillas_aprobadas_final'] = base_queryset.filter(estado='aprobada_final').count()
        context['planillas_pagadas'] = base_queryset.filter(estado='pagada').count()
        
        # Totales en córdobas
        totales = base_queryset.filter(
            estado__in=['aprobada_final', 'pagada']
        ).aggregate(
            total_cordobas=Sum('total_cordobas'),
            total_dolares=Sum('total_dolares')
        )
        context['total_monto_cordobas'] = totales['total_cordobas'] or 0
        context['total_monto_dolares'] = totales['total_dolares'] or 0
        
        # Listas para filtros
        context['proyectos'] = Proyecto.objects.filter(eliminado=False).order_by('nombre')
        context['estados'] = Planilla.ESTADO_CHOICES
        
        # Valores actuales de filtros
        context['proyecto_actual'] = self.request.GET.get('proyecto', 'todos')
        context['estado_actual'] = self.request.GET.get('estado', 'todos')
        context['search_query'] = self.request.GET.get('search', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        
        # Tipo de cambio actual
        context['tipo_cambio_actual'] = TipoCambio.get_actual()
        
        return context

class PlanillaCreateView(LoginRequiredMixin, View):
    """Vista para crear/generar una nueva planilla"""
    
    template_name = 'planillas/crear.html'
    
    def get(self, request):
        """Muestra el formulario de generación"""
        
        # Obtener proyectos activos
        proyectos = Proyecto.objects.filter(
            eliminado=False,
            estado__in=['planificacion', 'ejecucion']
        ).order_by('nombre')
        
        # Sugerir período por defecto (última catorcena)
        hoy = timezone.now().date()
        
        # Encontrar el jueves más reciente
        dias_desde_jueves = (hoy.weekday() - 3) % 7
        if dias_desde_jueves < 0:
            dias_desde_jueves += 7
        ultimo_jueves = hoy - timedelta(days=dias_desde_jueves)
        
        # Período sugerido: jueves a martes (13 días)
        periodo_inicio_sugerido = ultimo_jueves - timedelta(days=14)
        periodo_fin_sugerido = periodo_inicio_sugerido + timedelta(days=12)
        
        # Tipo de cambio actual
        tipo_cambio = TipoCambio.get_actual()
        
        context = {
            'proyectos': proyectos,
            'periodo_inicio_sugerido': periodo_inicio_sugerido,
            'periodo_fin_sugerido': periodo_fin_sugerido,
            'tipo_cambio': tipo_cambio,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Procesa la generación de la planilla"""
        
        action = request.POST.get('action')
        
        print(f"DEBUG: Action recibida: {action}")
        print(f"DEBUG: POST data: {request.POST}")
        
        # ============================================================
        # ACCIÓN: PREVIEW
        # ============================================================
        if action == 'preview':
            return self.preview_planilla(request)
        
        # ============================================================
        # ACCIÓN: GENERAR
        # ============================================================
        elif action == 'generar':
            return self.generar_planilla(request)
        
        # Acción no válida
        messages.error(request, f'Acción no válida: {action}')
        return redirect('planilla_crear')
    
    def preview_planilla(self, request):
        """Muestra un preview de la planilla antes de generarla"""
        
        try:
            print("DEBUG: Iniciando preview_planilla")
            
            # Obtener datos del formulario
            proyecto_id = request.POST.get('proyecto')
            periodo_inicio_str = request.POST.get('periodo_inicio')
            periodo_fin_str = request.POST.get('periodo_fin')
            
            print(f"DEBUG: proyecto_id={proyecto_id}, inicio={periodo_inicio_str}, fin={periodo_fin_str}")
            
            # Validar datos
            if not all([proyecto_id, periodo_inicio_str, periodo_fin_str]):
                messages.error(request, 'Todos los campos son obligatorios')
                return redirect('planilla_crear')
            
            # Convertir fechas
            try:
                periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
                periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()
            except ValueError as e:
                messages.error(request, f'Error en formato de fecha: {str(e)}')
                return redirect('planilla_crear')
            
            # Obtener proyecto
            try:
                proyecto = Proyecto.objects.get(id=proyecto_id, eliminado=False)
                print(f"DEBUG: Proyecto encontrado: {proyecto.nombre}")
            except Proyecto.DoesNotExist:
                messages.error(request, 'Proyecto no encontrado')
                return redirect('planilla_crear')
            
            # Validar período
            validacion = validar_periodo_planilla(periodo_inicio, periodo_fin)
            print(f"DEBUG: Validación período: {validacion}")
            
            if not validacion['valido']:
                for advertencia in validacion['advertencias']:
                    messages.error(request, advertencia)
                return redirect('planilla_crear')
            
            # Obtener resumen de asistencias
            resumen = obtener_resumen_asistencias(proyecto, periodo_inicio, periodo_fin)
            print(f"DEBUG: Resumen asistencias: {resumen}")
            
            # Verificar que haya asistencias validadas
            if not resumen['puede_generar']:
                messages.error(
                    request,
                    f'No hay asistencias validadas en el período seleccionado para el proyecto {proyecto.nombre}'
                )
                return redirect('planilla_crear')
            
            # Obtener asistencias
            asistencias = Asistencia.objects.filter(
                proyecto=proyecto,
                fecha__gte=periodo_inicio,
                fecha__lte=periodo_fin,
                validado=True
            ).select_related('trabajador')
            
            print(f"DEBUG: Asistencias encontradas: {asistencias.count()}")
            
            if not asistencias.exists():
                messages.error(request, 'No hay asistencias validadas en el período')
                return redirect('planilla_crear')
            
            # Agrupar por trabajador
            trabajadores_dict = {}
            for asistencia in asistencias:
                trabajador_id = asistencia.trabajador_id
                if trabajador_id not in trabajadores_dict:
                    trabajadores_dict[trabajador_id] = {
                        'trabajador': asistencia.trabajador,
                        'dias': 0,
                        'horas_normales': Decimal('0.00'),
                        'horas_extras': Decimal('0.00'),
                        'horas_dominicales': Decimal('0.00'),
                        'salario_dia': asistencia.salario_dia or asistencia.trabajador.salario_normal or Decimal('350.00'),
                    }
                
                if asistencia.estado == 'cerrado':
                    trabajadores_dict[trabajador_id]['dias'] += 1
                
                trabajadores_dict[trabajador_id]['horas_normales'] += asistencia.horas_normales or Decimal('0.00')
                trabajadores_dict[trabajador_id]['horas_extras'] += asistencia.horas_extras or Decimal('0.00')
                
                # Si es domingo, sumar a horas dominicales
                if asistencia.fecha.weekday() == 6:
                    trabajadores_dict[trabajador_id]['horas_dominicales'] += asistencia.horas_normales or Decimal('0.00')
            
            print(f"DEBUG: Trabajadores agrupados: {len(trabajadores_dict)}")
            
            # Calcular totales por trabajador
            preview_detalles = []
            total_general_cordobas = Decimal('0.00')
            tipo_cambio = TipoCambio.get_actual()
            
            for data in trabajadores_dict.values():
                trabajador = data['trabajador']
                salario_dia = data['salario_dia']
                
                # Cálculos según fórmulas
                valor_septimo_dia = (salario_dia / Decimal('6')).quantize(Decimal('0.01'))
                salario_diario_con_septimo = salario_dia + valor_septimo_dia
                valor_hora_base = (salario_dia / Decimal('12')).quantize(Decimal('0.01'))
                
                salario_devengado = (salario_diario_con_septimo * Decimal(str(data['dias']))).quantize(Decimal('0.01'))
                salario_horas_extras = ((valor_hora_base * Decimal('2')) * data['horas_extras']).quantize(Decimal('0.01'))
                salario_horas_dominicales = ((valor_hora_base * Decimal('2')) * data['horas_dominicales']).quantize(Decimal('0.01'))
                
                ingreso_total = salario_devengado + salario_horas_extras + salario_horas_dominicales
                total_general_cordobas += ingreso_total
                
                preview_detalles.append({
                    'trabajador': trabajador,
                    'dias': data['dias'],
                    'horas_extras': data['horas_extras'],
                    'horas_dominicales': data['horas_dominicales'],
                    'salario_dia': salario_dia,
                    'ingreso_total': ingreso_total,
                    'ingreso_total_dolares': (ingreso_total / tipo_cambio.valor).quantize(Decimal('0.01')),
                })
            
            total_general_dolares = (total_general_cordobas / tipo_cambio.valor).quantize(Decimal('0.01'))
            
            print(f"DEBUG: Detalles calculados: {len(preview_detalles)}")
            print(f"DEBUG: Total córdobas: {total_general_cordobas}")
            
            # Mostrar advertencias si las hay
            if validacion['advertencias']:
                for advertencia in validacion['advertencias']:
                    messages.warning(request, f"⚠️ {advertencia}")
            
            # Obtener proyectos y tipo de cambio para el contexto
            proyectos = Proyecto.objects.filter(
                eliminado=False,
                estado__in=['planificacion', 'ejecucion']
            ).order_by('nombre')
            
            context = {
                'proyectos': proyectos,
                'proyecto': proyecto,
                'periodo_inicio': periodo_inicio,
                'periodo_fin': periodo_fin,
                'validacion': validacion,
                'resumen': resumen,
                'preview_detalles': preview_detalles,
                'total_general_cordobas': total_general_cordobas,
                'total_general_dolares': total_general_dolares,
                'tipo_cambio': tipo_cambio,
                'mostrar_preview': True,
            }
            
            print("DEBUG: Renderizando template con preview")
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"ERROR en preview_planilla: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error al generar preview: {str(e)}')
            return redirect('planilla_crear')
    
    def generar_planilla(self, request):
        """Genera la planilla final y la guarda en BD"""
        
        try:
            print("DEBUG: Iniciando generar_planilla")
            
            # Obtener datos del formulario
            proyecto_id = request.POST.get('proyecto')
            periodo_inicio = datetime.strptime(request.POST.get('periodo_inicio'), '%Y-%m-%d').date()
            periodo_fin = datetime.strptime(request.POST.get('periodo_fin'), '%Y-%m-%d').date()
            
            # Obtener proyecto
            proyecto = get_object_or_404(Proyecto, id=proyecto_id, eliminado=False)
            
            print(f"DEBUG: Generando planilla para {proyecto.nombre}")
            
            # Generar planilla
            planilla, detalles, errores = generar_planilla_desde_asistencias(
                proyecto=proyecto,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
                usuario=request.user
            )
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return redirect('planilla_crear')
            
            if planilla:
                messages.success(
                    request,
                    f'✅ Planilla {planilla.codigo} generada exitosamente con {len(detalles)} trabajadores'
                )
                return redirect('planillas_lista')
            else:
                messages.error(request, 'No se pudo generar la planilla')
                return redirect('planilla_crear')
                
        except Exception as e:
            print(f"ERROR en generar_planilla: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error al generar planilla: {str(e)}')
            return redirect('planilla_crear')

class PlanillaDetalleView(LoginRequiredMixin, View):
    """Vista para ver el detalle completo de una planilla"""
    
    template_name = 'planillas/detalle.html'
    
    def get(self, request, pk):
        """Muestra el detalle de la planilla"""
        
        # Obtener la planilla
        planilla = get_object_or_404(
            Planilla.objects.select_related(
                'proyecto',
                'generada_por',
                'aprobada_gerente_por',
                'aprobada_contador_por'
            ),
            pk=pk,
            eliminado=False
        )
        
        # Obtener detalles de la planilla
        detalles = DetallePlanilla.objects.filter(
            planilla=planilla
        ).select_related('trabajador').order_by('area', 'trabajador__nombre', 'trabajador__apellido')
        
        # Agrupar por área
        detalles_por_area = {}
        for detalle in detalles:
            area = detalle.get_area_display()
            if area not in detalles_por_area:
                detalles_por_area[area] = []
            detalles_por_area[area].append(detalle)
        
        # Calcular totales por área
        totales_por_area = {}
        for area, detalles_area in detalles_por_area.items():
            total_cordobas = sum(d.ingreso_total for d in detalles_area)
            total_dolares = sum(d.ingreso_total_dolares for d in detalles_area)
            totales_por_area[area] = {
                'cantidad': len(detalles_area),
                'total_cordobas': total_cordobas,
                'total_dolares': total_dolares
            }
        
        # Obtener rol del usuario de forma segura
        user_rol = getattr(request.user, 'rol', None)
        
        # Permisos del usuario
        puede_editar = planilla.estado == 'borrador' and (
            request.user.is_superuser or 
            request.user == planilla.generada_por
        )
        
        puede_aprobar_gerente = (
            planilla.estado == 'borrador' and
            (request.user.is_superuser or user_rol in ['gerente', 'administrador'])
        )
        
        puede_aprobar_contador = (
            planilla.estado == 'aprobada_gerente' and
            (request.user.is_superuser or user_rol in ['contador', 'administrador'])
        )
        
        puede_marcar_pagada = (
            planilla.estado == 'aprobada_final' and
            (request.user.is_superuser or user_rol in ['contador', 'administrador'])
        )
        
        context = {
            'planilla': planilla,
            'detalles': detalles,
            'detalles_por_area': detalles_por_area,
            'totales_por_area': totales_por_area,
            'puede_editar': puede_editar,
            'puede_aprobar_gerente': puede_aprobar_gerente,
            'puede_aprobar_contador': puede_aprobar_contador,
            'puede_marcar_pagada': puede_marcar_pagada,
        }
        
        return render(request, self.template_name, context)


class PlanillaEditarDetalleView(LoginRequiredMixin, View):
    """Vista para editar bonos y deducciones de un detalle de planilla"""
    
    def post(self, request, pk):
        """Actualiza los bonos y deducciones de un detalle"""
        
        # Obtener objetos principales primero
        detalle = get_object_or_404(DetallePlanilla, pk=pk)
        planilla = detalle.planilla

        try:
            # 1. Verificar que la planilla esté en borrador
            if planilla.estado != 'borrador':
                messages.error(request, 'Solo se pueden editar planillas en estado borrador')
                return redirect('planilla_detalle', pk=planilla.pk)
            
            # 2. Obtener datos del formulario
            bonos_str = request.POST.get('bonos', '0')
            deducciones_str = request.POST.get('deducciones', '0')
            observaciones = request.POST.get('observaciones', '')

            # 3. Limpieza de datos (para aceptar '.' o ',')
            # Reemplaza comas por puntos y maneja strings vacíos
            bonos_clean = bonos_str.strip().replace(',', '.') if bonos_str else '0'
            deducciones_clean = deducciones_str.strip().replace(',', '.') if deducciones_str else '0'
            
            # 4. Asignar valores al detalle
            detalle.bonos = Decimal(bonos_clean)
            detalle.deducciones = Decimal(deducciones_clean) # Asumiendo que ya añadiste este campo al modelo
            detalle.observaciones = observaciones
            
            # 5. Guardar y recalcular
            # El método .save() de DetallePlanilla (que modificaste)
            # se encargará de llamar a calcular_valores()
            # y planilla.calcular_totales()
            detalle.save()
            
            # 6. Mensaje de éxito (SOLO si todo salió bien)
            messages.success(
                request,
                f'✅ Detalle actualizado para {detalle.trabajador.nombre} {detalle.trabajador.apellido}'
            )
            
        except Exception as e:
            # Informar cualquier error (ej. '150.abc' no es un decimal válido)
            messages.error(request, f'Error al actualizar: {str(e)}')
        
        # 7. Redirigir de vuelta a la planilla
        return redirect('planilla_detalle', pk=planilla.pk)

class PlanillaAprobarGerenteView(LoginRequiredMixin, View):
    """Vista para aprobar planilla como gerente"""
    
    def post(self, request, pk):
        """Aprueba la planilla como gerente"""
        
        try:
            planilla = get_object_or_404(Planilla, pk=pk, eliminado=False)
            
            # Verificar estado
            if planilla.estado != 'borrador':
                messages.error(request, 'Solo se pueden aprobar planillas en estado borrador')
                return redirect('planilla_detalle', pk=pk)
            
            # Verificar permisos
            user_rol = getattr(request.user, 'rol', None)
            if not (request.user.is_superuser or user_rol in ['gerente', 'administrador']):
                messages.error(request, 'No tienes permisos para aprobar como gerente')
                return redirect('planilla_detalle', pk=pk)
            
            # Aprobar
            planilla.estado = 'aprobada_gerente'
            planilla.aprobada_gerente_por = request.user
            planilla.aprobada_gerente_fecha = timezone.now()
            planilla.save()
            
            messages.success(
                request,
                f'✅ Planilla {planilla.codigo} aprobada como gerente. Ahora debe aprobarla el contador.'
            )
            
        except Exception as e:
            messages.error(request, f'Error al aprobar: {str(e)}')
        
        return redirect('planilla_detalle', pk=pk)


class PlanillaAprobarContadorView(LoginRequiredMixin, View):
    """Vista para aprobar planilla como contador"""
    
    def post(self, request, pk):
        """Aprueba la planilla como contador (aprobación final)"""
        
        try:
            planilla = get_object_or_404(Planilla, pk=pk, eliminado=False)
            
            # Verificar estado
            if planilla.estado != 'aprobada_gerente':
                messages.error(request, 'La planilla debe estar aprobada por el gerente primero')
                return redirect('planilla_detalle', pk=pk)
            
            # Verificar permisos
            user_rol = getattr(request.user, 'rol', None)
            if not (request.user.is_superuser or user_rol in ['contador', 'administrador']):
                messages.error(request, 'No tienes permisos para aprobar como contador')
                return redirect('planilla_detalle', pk=pk)
            
            # Aprobar
            planilla.estado = 'aprobada_final'
            planilla.aprobada_contador_por = request.user
            planilla.aprobada_contador_fecha = timezone.now()
            planilla.save()
            
            messages.success(
                request,
                f'✅ Planilla {planilla.codigo} aprobada finalmente. Lista para pago.'
            )
            
        except Exception as e:
            messages.error(request, f'Error al aprobar: {str(e)}')
        
        return redirect('planilla_detalle', pk=pk)


class PlanillaMarcarPagadaView(LoginRequiredMixin, View):
    """Vista para marcar planilla como pagada"""
    
    def post(self, request, pk):
        """Marca la planilla como pagada"""
        
        try:
            planilla = get_object_or_404(Planilla, pk=pk, eliminado=False)
            
            # Verificar estado
            if planilla.estado != 'aprobada_final':
                messages.error(request, 'La planilla debe estar aprobada finalmente')
                return redirect('planilla_detalle', pk=pk)
            
            # Verificar permisos
            user_rol = getattr(request.user, 'rol', None)
            if not (request.user.is_superuser or user_rol in ['contador', 'administrador']):
                messages.error(request, 'No tienes permisos para marcar como pagada')
                return redirect('planilla_detalle', pk=pk)
            
            # Marcar como pagada
            planilla.estado = 'pagada'
            planilla.fecha_pago = timezone.now().date()
            planilla.save()
            
            messages.success(
                request,
                f'✅ Planilla {planilla.codigo} marcada como pagada.'
            )
            
        except Exception as e:
            messages.error(request, f'Error al marcar como pagada: {str(e)}')
        
        return redirect('planilla_detalle', pk=pk)


class PlanillaEliminarView(LoginRequiredMixin, View):
    """Vista para eliminar (soft delete) una planilla"""
    
    def post(self, request, pk):
        """Elimina la planilla (soft delete)"""
        
        try:
            planilla = get_object_or_404(Planilla, pk=pk, eliminado=False)
            
            # Solo se pueden eliminar borradores
            if planilla.estado != 'borrador':
                messages.error(request, 'Solo se pueden eliminar planillas en estado borrador')
                return redirect('planilla_detalle', pk=pk)
            
            # Verificar permisos
            if not (request.user.is_superuser or request.user == planilla.generada_por):
                messages.error(request, 'No tienes permisos para eliminar esta planilla')
                return redirect('planilla_detalle', pk=pk)
            
            # Soft delete
            planilla.eliminado = True
            planilla.save()
            
            messages.success(
                request,
                f'✅ Planilla {planilla.codigo} eliminada correctamente.'
            )
            
            return redirect('planillas_lista')
            
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('planilla_detalle', pk=pk)

