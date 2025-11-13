"""
Vistas del módulo de planillas
apps/planillas/views.py
"""
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

import traceback
import io

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

class PlanillaExportarExcelView(LoginRequiredMixin, View):
    """Vista para exportar planilla a Excel"""
    
    def get(self, request, pk):
        """Genera y descarga el archivo Excel de la planilla"""
        
        # Obtener la planilla
        planilla = get_object_or_404(
            Planilla.objects.select_related('proyecto', 'generada_por'),
            pk=pk,
            eliminado=False
        )
        
        # Obtener detalles agrupados por área
        detalles = DetallePlanilla.objects.filter(
            planilla=planilla
        ).select_related('trabajador').order_by('area', 'trabajador__nombre', 'trabajador__apellido')
        
        # Crear el libro de Excel
        wb = Workbook()
        ws = wb.active
        ws.title = f"Planilla {planilla.codigo}"
        
        # ============================================================
        # 1. ENCABEZADO
        # ============================================================
        
        # Logo y nombre de la empresa (fila 1-2)
        ws.merge_cells('A1:L1')
        cell_titulo = ws['A1']
        cell_titulo.value = "SISTEMA DE PLANILLAS"
        cell_titulo.font = Font(name='Arial', size=16, bold=True, color='FFFFFF')
        cell_titulo.fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
        cell_titulo.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30
        
        # Información de la planilla (fila 3-6)
        ws.merge_cells('A3:L3')
        cell_codigo = ws['A3']
        cell_codigo.value = f"PLANILLA DE PAGO - {planilla.codigo}"
        cell_codigo.font = Font(name='Arial', size=14, bold=True)
        cell_codigo.alignment = Alignment(horizontal='center')
        
        # Datos del proyecto
        row = 5
        info_data = [
            ('Proyecto:', planilla.proyecto.nombre),
            ('Período:', f"{planilla.periodo_inicio.strftime('%d/%m/%Y')} - {planilla.periodo_fin.strftime('%d/%m/%Y')}"),
            ('Estado:', planilla.get_estado_display()),
            ('Tipo de Cambio:', f"C$ {planilla.tipo_cambio}"),
            ('Fecha de Generación:', planilla.fecha_generacion.strftime('%d/%m/%Y %H:%M')),
        ]
        
        for label, value in info_data:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(name='Arial', size=10, bold=True)
            ws[f'B{row}'] = value
            ws[f'B{row}'].font = Font(name='Arial', size=10)
            ws.merge_cells(f'B{row}:D{row}')
            row += 1
        
        # ============================================================
        # 2. ENCABEZADOS DE TABLA
        # ============================================================
        
        row += 2  # Espacio
        header_row = row
        
        headers = [
            'Trabajador',
            'Cargo',
            'Días',
            'H. Extras',
            'H. Dom.',
            'Salario Base',
            'Bonos',
            'Deducciones',
            'Total C$',
            'INSS Lab.',
            'INSS Pat.',
            'INATEC'
        ]
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_num)
            cell.value = header
            cell.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        
        ws.row_dimensions[header_row].height = 30
        
        # ============================================================
        # 3. DATOS POR ÁREA
        # ============================================================
        
        row = header_row + 1
        
        # Agrupar por área
        detalles_por_area = {}
        for detalle in detalles:
            area = detalle.get_area_display()
            if area not in detalles_por_area:
                detalles_por_area[area] = []
            detalles_por_area[area].append(detalle)
        
        # Estilos para las celdas de datos
        border_thin = Border(
            left=Side(style='thin', color='CCCCCC'),
            right=Side(style='thin', color='CCCCCC'),
            top=Side(style='thin', color='CCCCCC'),
            bottom=Side(style='thin', color='CCCCCC')
        )
        
        # Recorrer cada área
        for area, detalles_area in detalles_por_area.items():
            # Header del área
            ws.merge_cells(f'A{row}:L{row}')
            cell_area = ws[f'A{row}']
            cell_area.value = f"📋 {area.upper()} ({len(detalles_area)} trabajadores)"
            cell_area.font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
            cell_area.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell_area.alignment = Alignment(horizontal='left', vertical='center')
            ws.row_dimensions[row].height = 25
            row += 1
            
            # Datos de cada trabajador
            for detalle in detalles_area:
                data_row = [
                    f"{detalle.trabajador.nombre} {detalle.trabajador.apellido}",
                    detalle.cargo,
                    detalle.dias_laborados,
                    float(detalle.horas_extras),
                    float(detalle.horas_dominicales),
                    float(detalle.salario_dia_base),
                    float(detalle.bonos),
                    float(detalle.deducciones),
                    float(detalle.ingreso_total),
                    float(detalle.inss_laboral),
                    float(detalle.inss_patronal),
                    float(detalle.inatec),
                ]
                
                for col_num, value in enumerate(data_row, 1):
                    cell = ws.cell(row=row, column=col_num)
                    cell.value = value
                    cell.border = border_thin
                    cell.font = Font(name='Arial', size=9)
                    
                    # Alineación
                    if col_num <= 2:  # Texto
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                    else:  # Números
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                    
                    # Formato de moneda para columnas de dinero
                    if col_num >= 6:
                        cell.number_format = '#,##0.00'
                
                row += 1
            
            # Subtotal del área
            total_area = sum(d.ingreso_total for d in detalles_area)
            ws.merge_cells(f'A{row}:H{row}')
            cell_subtotal = ws[f'A{row}']
            cell_subtotal.value = f"SUBTOTAL {area.upper()}"
            cell_subtotal.font = Font(name='Arial', size=10, bold=True)
            cell_subtotal.fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
            cell_subtotal.alignment = Alignment(horizontal='right', vertical='center')
            
            cell_total = ws.cell(row=row, column=9)
            cell_total.value = float(total_area)
            cell_total.font = Font(name='Arial', size=10, bold=True)
            cell_total.fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
            cell_total.alignment = Alignment(horizontal='right', vertical='center')
            cell_total.number_format = '#,##0.00'
            
            row += 2  # Espacio entre áreas
        
        # ============================================================
        # 4. TOTALES GENERALES
        # ============================================================
        
        row += 1
        
        # Fila de totales
        ws.merge_cells(f'A{row}:H{row}')
        cell_total_label = ws[f'A{row}']
        cell_total_label.value = "TOTAL GENERAL"
        cell_total_label.font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
        cell_total_label.fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
        cell_total_label.alignment = Alignment(horizontal='right', vertical='center')
        
        cell_total_valor = ws.cell(row=row, column=9)
        cell_total_valor.value = float(planilla.total_cordobas)
        cell_total_valor.font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
        cell_total_valor.fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
        cell_total_valor.alignment = Alignment(horizontal='right', vertical='center')
        cell_total_valor.number_format = '#,##0.00'
        
        ws.row_dimensions[row].height = 25
        
        # ============================================================
        # 5. RESUMEN DE CONTRIBUCIONES
        # ============================================================
        
        row += 3
        
        ws[f'A{row}'] = "RESUMEN DE CONTRIBUCIONES"
        ws[f'A{row}'].font = Font(name='Arial', size=12, bold=True)
        ws.merge_cells(f'A{row}:L{row}')
        
        row += 1
        
        contribuciones = [
            ('Total en Córdobas:', float(planilla.total_cordobas), 'C$'),
            ('Total en Dólares:', float(planilla.total_dolares), '$'),
            ('INSS Laboral (6.25%):', float(planilla.total_inss_laboral), 'C$'),
            ('INSS Patronal (19%):', float(planilla.total_inss_patronal), 'C$'),
            ('INATEC (2%):', float(planilla.total_inatec), 'C$'),
        ]
        
        for label, value, moneda in contribuciones:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(name='Arial', size=10, bold=True)
            ws[f'B{row}'] = f"{moneda} {value:,.2f}"
            ws[f'B{row}'].font = Font(name='Arial', size=10)
            ws[f'B{row}'].number_format = '#,##0.00'
            ws.merge_cells(f'B{row}:D{row}')
            row += 1
        
        # ============================================================
        # 6. FIRMAS
        # ============================================================
        
        row += 3
        
        firmas = [
            ('Generado por:', planilla.generada_por.get_full_name() if planilla.generada_por else ''),
            ('Aprobado por Gerente:', planilla.aprobada_gerente_por.get_full_name() if planilla.aprobada_gerente_por else ''),
            ('Aprobado por Contador:', planilla.aprobada_contador_por.get_full_name() if planilla.aprobada_contador_por else ''),
        ]
        
        col_firma = 1
        for label, nombre in firmas:
            ws.cell(row=row, column=col_firma).value = label
            ws.cell(row=row, column=col_firma).font = Font(name='Arial', size=9, bold=True)
            ws.cell(row=row+1, column=col_firma).value = nombre
            ws.cell(row=row+1, column=col_firma).font = Font(name='Arial', size=9)
            ws.cell(row=row+2, column=col_firma).value = "________________________"
            ws.cell(row=row+2, column=col_firma).alignment = Alignment(horizontal='center')
            col_firma += 4
        
        # ============================================================
        # 7. AJUSTAR ANCHOS DE COLUMNAS
        # ============================================================
        
        column_widths = {
            'A': 25,  # Trabajador
            'B': 20,  # Cargo
            'C': 8,   # Días
            'D': 10,  # H. Extras
            'E': 10,  # H. Dom.
            'F': 12,  # Salario Base
            'G': 10,  # Bonos
            'H': 12,  # Deducciones
            'I': 12,  # Total C$
            'J': 12,  # INSS Lab.
            'K': 12,  # INSS Pat.
            'L': 10,  # INATEC
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # ============================================================
        # 8. GENERAR ARCHIVO Y ENVIAR
        # ============================================================
        
        # Crear archivo en memoria
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Crear respuesta HTTP
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f"Planilla_{planilla.codigo}_{planilla.proyecto.nombre.replace(' ', '_')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

class PlanillaExportarPDFView(LoginRequiredMixin, View):
    """Vista para exportar planilla a PDF"""
    
    def get(self, request, pk):
        """Genera y descarga el archivo PDF de la planilla"""
        
        # Obtener la planilla
        planilla = get_object_or_404(
            Planilla.objects.select_related('proyecto', 'generada_por'),
            pk=pk,
            eliminado=False
        )
        
        # Obtener detalles agrupados por área
        detalles = DetallePlanilla.objects.filter(
            planilla=planilla
        ).select_related('trabajador').order_by('area', 'trabajador__nombre', 'trabajador__apellido')
        
        # Crear el buffer para el PDF
        buffer = io.BytesIO()
        
        # Crear el documento PDF (tamaño carta, horizontal para más espacio)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )
        
        # Container para los elementos del PDF
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1F4788'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulos
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1F4788'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para texto normal
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=6,
        )
        
        # ============================================================
        # 1. ENCABEZADO
        # ============================================================
        
        # Título principal
        title = Paragraph("SISTEMA DE PLANILLAS", title_style)
        elements.append(title)
        
        # Subtítulo con código
        subtitle = Paragraph(f"PLANILLA DE PAGO - {planilla.codigo}", subtitle_style)
        elements.append(subtitle)
        
        elements.append(Spacer(1, 0.2 * inch))
        
        # ============================================================
        # 2. INFORMACIÓN DEL PROYECTO
        # ============================================================
        
        info_data = [
            ['Proyecto:', planilla.proyecto.nombre],
            ['Período:', f"{planilla.periodo_inicio.strftime('%d/%m/%Y')} - {planilla.periodo_fin.strftime('%d/%m/%Y')}"],
            ['Estado:', planilla.get_estado_display()],
            ['Tipo de Cambio:', f"C$ {planilla.tipo_cambio}"],
            ['Fecha de Generación:', planilla.fecha_generacion.strftime('%d/%m/%Y %H:%M')],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # ============================================================
        # 3. TABLA DE TRABAJADORES POR ÁREA
        # ============================================================
        
        # Agrupar por área
        detalles_por_area = {}
        for detalle in detalles:
            area = detalle.get_area_display()
            if area not in detalles_por_area:
                detalles_por_area[area] = []
            detalles_por_area[area].append(detalle)
        
        # Headers de la tabla
        headers = [
            'Trabajador',
            'Cargo',
            'Días',
            'H.Ext',
            'H.Dom',
            'Sal.Base',
            'Bonos',
            'Deduc.',
            'Total C$'
        ]
        
        # Recorrer cada área
        for area, detalles_area in detalles_por_area.items():
            # Título del área
            area_title = Paragraph(
                f"<b>{area.upper()} ({len(detalles_area)} trabajadores)</b>",
                ParagraphStyle(
                    'AreaTitle',
                    parent=styles['Heading3'],
                    fontSize=11,
                    textColor=colors.white,
                    backColor=colors.HexColor('#4472C4'),
                    spaceAfter=6,
                    spaceBefore=6,
                    leftIndent=6,
                    fontName='Helvetica-Bold'
                )
            )
            elements.append(area_title)
            
            # Datos de la tabla
            table_data = [headers]
            
            for detalle in detalles_area:
                row = [
                    f"{detalle.trabajador.nombre} {detalle.trabajador.apellido}",
                    detalle.cargo[:20],  # Truncar si es muy largo
                    str(detalle.dias_laborados),
                    f"{float(detalle.horas_extras):.1f}",
                    f"{float(detalle.horas_dominicales):.1f}",
                    f"{float(detalle.salario_dia_base):,.2f}",
                    f"{float(detalle.bonos):,.2f}",
                    f"{float(detalle.deducciones):,.2f}",
                    f"{float(detalle.ingreso_total):,.2f}",
                ]
                table_data.append(row)
            
            # Subtotal del área
            total_area = sum(d.ingreso_total for d in detalles_area)
            subtotal_row = [
                'SUBTOTAL',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                f"{float(total_area):,.2f}"
            ]
            table_data.append(subtotal_row)
            
            # Crear tabla
            col_widths = [1.8*inch, 1.2*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.7*inch, 0.6*inch, 0.6*inch, 0.8*inch]
            
            area_table = Table(table_data, colWidths=col_widths)
            area_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Datos
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('ALIGN', (0, 1), (1, -2), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -2), 'RIGHT'),
                
                # Subtotal
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E7E6E6')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
                ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
                ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
                
                # Bordes
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(area_table)
            elements.append(Spacer(1, 0.2 * inch))
        
        # ============================================================
        # 4. TOTAL GENERAL
        # ============================================================
        
        total_data = [
            ['TOTAL GENERAL', f"C$ {float(planilla.total_cordobas):,.2f}"]
        ]
        
        total_table = Table(total_data, colWidths=[5.5*inch, 1.4*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1F4788')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(total_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # ============================================================
        # 5. RESUMEN DE CONTRIBUCIONES
        # ============================================================
        
        contribuciones_title = Paragraph("<b>RESUMEN DE CONTRIBUCIONES</b>", subtitle_style)
        elements.append(contribuciones_title)
        
        contribuciones_data = [
            ['Total en Córdobas:', f"C$ {float(planilla.total_cordobas):,.2f}"],
            ['Total en Dólares:', f"$ {float(planilla.total_dolares):,.2f}"],
            ['INSS Laboral (6.25%):', f"C$ {float(planilla.total_inss_laboral):,.2f}"],
            ['INSS Patronal (19%):', f"C$ {float(planilla.total_inss_patronal):,.2f}"],
            ['INATEC (2%):', f"C$ {float(planilla.total_inatec):,.2f}"],
        ]
        
        contrib_table = Table(contribuciones_data, colWidths=[3*inch, 2*inch])
        contrib_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(contrib_table)
        elements.append(Spacer(1, 0.4 * inch))
        
        # ============================================================
        # 6. FIRMAS
        # ============================================================
        
        firmas_data = [
            ['Generado por:', 'Aprobado por Gerente:', 'Aprobado por Contador:'],
            [
                planilla.generada_por.get_full_name() if planilla.generada_por else '',
                planilla.aprobada_gerente_por.get_full_name() if planilla.aprobada_gerente_por else '',
                planilla.aprobada_contador_por.get_full_name() if planilla.aprobada_contador_por else ''
            ],
            ['_' * 25, '_' * 25, '_' * 25],
        ]
        
        firmas_table = Table(firmas_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
        firmas_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(firmas_table)
        
        # ============================================================
        # 7. GENERAR PDF
        # ============================================================
        
        # Construir el PDF
        doc.build(elements)
        
        # Obtener el valor del buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Crear respuesta HTTP
        response = HttpResponse(content_type='application/pdf')
        filename = f"Planilla_{planilla.codigo}_{planilla.proyecto.nombre.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf)
        
        return response

