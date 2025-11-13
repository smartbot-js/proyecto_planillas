"""
Utilidades para el módulo de planillas - CORREGIDO
apps/planillas/utils.py
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import Planilla, DetallePlanilla, DiaFeriado, TipoCambio
from apps.asistencias.models import Asistencia
from apps.trabajadores.models import Trabajador


def generar_planilla_desde_asistencias(proyecto, periodo_inicio, periodo_fin, usuario):
    """
    Genera una planilla automáticamente desde las asistencias validadas
    
    Args:
        proyecto: Instancia de Proyecto
        periodo_inicio: fecha de inicio del período
        periodo_fin: fecha de fin del período
        usuario: Usuario que genera la planilla
        
    Returns:
        tuple: (planilla, detalles_list, errores_list)
    """
    errores = []
    
    # ============================================================
    # 1. VALIDACIONES PREVIAS
    # ============================================================
    
    # Verificar que no exista ya una planilla para este proyecto y período
    planilla_existente = Planilla.objects.filter(
        proyecto=proyecto,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        eliminado=False
    ).first()
    
    if planilla_existente:
        errores.append(f"Ya existe una planilla para este proyecto y período: {planilla_existente.codigo}")
        return None, [], errores
    
    # Verificar que haya asistencias en el período
    asistencias = Asistencia.objects.filter(
        proyecto=proyecto,
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin,
        validado=True  # Solo asistencias validadas
    )
    
    if not asistencias.exists():
        errores.append("No hay asistencias validadas en el período seleccionado")
        return None, [], errores
    
    # ============================================================
    # 2. OBTENER TIPO DE CAMBIO ACTUAL
    # ============================================================
    tipo_cambio = TipoCambio.get_actual()
    
    # ============================================================
    # 3. CREAR LA PLANILLA (EN BORRADOR)
    # ============================================================
    try:
        planilla = Planilla.objects.create(
            proyecto=proyecto,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            tipo_cambio=tipo_cambio.valor,
            estado='borrador',
            generada_por=usuario
        )
    except Exception as e:
        errores.append(f"Error al crear la planilla: {str(e)}")
        return None, [], errores
    
    # ============================================================
    # 4. AGRUPAR ASISTENCIAS POR TRABAJADOR
    # ============================================================
    trabajadores_ids = asistencias.values_list('trabajador_id', flat=True).distinct()
    detalles_list = []
    
    for trabajador_id in trabajadores_ids:
        trabajador = Trabajador.objects.get(id=trabajador_id)
        
        # Verificar si ya existe un detalle para este trabajador (evitar duplicados)
        detalle_existente = DetallePlanilla.objects.filter(
            planilla=planilla,
            trabajador=trabajador
        ).first()
        
        if detalle_existente:
            # Si ya existe, saltarlo (no debería pasar, pero por seguridad)
            continue
        
        # Obtener asistencias del trabajador en el período
        asistencias_trabajador = asistencias.filter(trabajador=trabajador)
        
        # ============================================================
        # 5. CALCULAR DÍAS LABORADOS
        # ============================================================
        dias_laborados = asistencias_trabajador.filter(
            estado='cerrado'  # Solo turnos cerrados
        ).count()
        
        # ============================================================
        # 6. CALCULAR HORAS
        # ============================================================
        # Horas normales
        horas_normales = asistencias_trabajador.aggregate(
            total=Sum('horas_normales')
        )['total'] or Decimal('0.00')
        
        # Horas extras
        horas_extras = asistencias_trabajador.aggregate(
            total=Sum('horas_extras')
        )['total'] or Decimal('0.00')
        
        # Horas dominicales (asistencias en domingo)
        horas_dominicales = Decimal('0.00')
        for asistencia in asistencias_trabajador:
            if asistencia.fecha.weekday() == 6:  # 6 = Domingo
                horas_dominicales += asistencia.horas_normales or Decimal('0.00')
        
        # Días feriados trabajados
        dias_feriados = 0
        for asistencia in asistencias_trabajador:
            if DiaFeriado.es_feriado(asistencia.fecha, proyecto):
                dias_feriados += 1
        
        # ============================================================
        # 7. OBTENER SALARIO BASE DEL TRABAJADOR
        # ============================================================
        # Usar el salario más reciente del trabajador en el período
        ultima_asistencia = asistencias_trabajador.order_by('-fecha').first()
        salario_dia_base = ultima_asistencia.salario_dia if ultima_asistencia and ultima_asistencia.salario_dia else (trabajador.salario_normal or Decimal('350.00'))
        
        # ============================================================
        # 8. DETERMINAR ÁREA DEL TRABAJADOR
        # ============================================================
        # Clasificar según el puesto laboral
        puesto = trabajador.puesto_laboral.lower()
        
        if any(word in puesto for word in ['secretaria', 'contador', 'gerente', 'administrador', 'analista']):
            area = 'administrativo'
        elif any(word in puesto for word in ['albañil', 'maestro', 'fontanero', 'electricista', 'soldador', 'oficial']):
            area = 'oficiales'
        elif any(word in puesto for word in ['ayudante', 'auxiliar', 'peon']):
            area = 'ayudantes'
        elif any(word in puesto for word in ['contratista', 'subcontratista']):
            area = 'subcontratista'
        else:
            area = 'oficiales'  # Default
        
        # ============================================================
        # 9. CREAR DETALLE DE PLANILLA
        # ============================================================
        try:
            detalle = DetallePlanilla.objects.create(
                planilla=planilla,
                trabajador=trabajador,
                area=area,
                cargo=trabajador.puesto_laboral,
                dias_laborados=dias_laborados,
                horas_normales=horas_normales,
                horas_extras=horas_extras,
                horas_dominicales=horas_dominicales,
                dias_feriados=dias_feriados,
                salario_dia_base=salario_dia_base,
                # Los demás campos se calculan automáticamente en el método save() del modelo
            )
            detalles_list.append(detalle)
        except Exception as e:
            # Si falla la creación de un detalle, registrar pero continuar
            print(f"Error al crear detalle para {trabajador.nombre_completo}: {str(e)}")
    
    # ============================================================
    # 10. CALCULAR TOTALES DE LA PLANILLA
    # ============================================================
    try:
        planilla.calcular_totales()
        planilla.save()
    except Exception as e:
        errores.append(f"Error al calcular totales: {str(e)}")
        # Eliminar la planilla si hubo error
        planilla.delete()
        return None, [], errores
    
    return planilla, detalles_list, errores


def validar_periodo_planilla(periodo_inicio, periodo_fin):
    """
    Valida el período de la planilla y retorna advertencias
    
    Returns:
        dict: {
            'valido': bool,
            'advertencias': list,
            'dias_periodo': int,
            'inicia_jueves': bool,
            'termina_martes': bool
        }
    """
    advertencias = []
    
    # Calcular días del período
    dias_periodo = (periodo_fin - periodo_inicio).days + 1
    
    # Verificar si inicia en jueves (weekday 3)
    inicia_jueves = periodo_inicio.weekday() == 3
    if not inicia_jueves:
        dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][periodo_inicio.weekday()]
        advertencias.append(f"El período no inicia en jueves (inicia en {dia_nombre})")
    
    # Verificar si termina en martes (weekday 1)
    termina_martes = periodo_fin.weekday() == 1
    if not termina_martes:
        dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][periodo_fin.weekday()]
        advertencias.append(f"El período no termina en martes (termina en {dia_nombre})")
    
    # Verificar que sea una catorcena (13 días: jueves a martes)
    if dias_periodo != 13 and inicia_jueves and termina_martes:
        advertencias.append(f"El período tiene {dias_periodo} días (se recomienda 13 días para catorcena)")
    
    # Verificar que periodo_fin sea posterior a periodo_inicio
    valido = periodo_fin > periodo_inicio
    if not valido:
        advertencias.append("La fecha de fin debe ser posterior a la fecha de inicio")
    
    return {
        'valido': valido,
        'advertencias': advertencias,
        'dias_periodo': dias_periodo,
        'inicia_jueves': inicia_jueves,
        'termina_martes': termina_martes
    }


def obtener_resumen_asistencias(proyecto, periodo_inicio, periodo_fin):
    """
    Obtiene un resumen de las asistencias en el período
    
    Returns:
        dict: Resumen con estadísticas
    """
    asistencias = Asistencia.objects.filter(
        proyecto=proyecto,
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin
    )
    
    total_asistencias = asistencias.count()
    asistencias_validadas = asistencias.filter(validado=True).count()
    asistencias_pendientes = total_asistencias - asistencias_validadas
    
    trabajadores_unicos = asistencias.values('trabajador').distinct().count()
    
    # ✅ CORREGIDO: Usar horas_normales en lugar de horas_trabajadas
    total_horas = asistencias.aggregate(
        horas=Sum('horas_normales')  # ✅ CAMPO CORRECTO
    )['horas'] or Decimal('0.00')
    
    total_horas_extras = asistencias.aggregate(
        extras=Sum('horas_extras')
    )['extras'] or Decimal('0.00')
    
    return {
        'total_asistencias': total_asistencias,
        'asistencias_validadas': asistencias_validadas,
        'asistencias_pendientes': asistencias_pendientes,
        'trabajadores_unicos': trabajadores_unicos,
        'total_horas': float(total_horas),
        'total_horas_extras': float(total_horas_extras),
        'puede_generar': asistencias_validadas > 0
    }
