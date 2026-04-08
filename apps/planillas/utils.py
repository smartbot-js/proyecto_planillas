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
from apps.asistencias.models import Asistencia

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
    # 4. OBTENER FERIADOS DEL PERÍODO
    # ============================================================
    feriados_periodo = set(DiaFeriado.objects.filter(
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin,
        activo=True
    ).filter(
        Q(tipo='nacional') | Q(proyecto=proyecto)
    ).values_list('fecha', flat=True))
    
    # ============================================================
    # 5. AGRUPAR ASISTENCIAS POR TRABAJADOR
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
        # dias_laborados = asistencias_trabajador.filter(
        #     estado='cerrado'  # Solo turnos cerrados
        # ).count()
        # Contar TODAS las asistencias validadas (abiertas o cerradas)
        # Para guardas, contar turnos; para normales, contar días
        if hasattr(trabajador, 'tipo_pago') and trabajador.tipo_pago == 'por_turno':
            from django.db.models import Sum
            dias_laborados = asistencias_trabajador.aggregate(
                total=Sum('turnos')
            )['total'] or 0
        else:
            dias_laborados = asistencias_trabajador.count()
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
        
        # Días feriados trabajados (con asistencia registrada = pago doble)
        dias_feriados = 0
        fechas_con_asistencia = set(asistencias_trabajador.values_list('fecha', flat=True))
        for fecha_asistencia in fechas_con_asistencia:
            if fecha_asistencia in feriados_periodo:
                dias_feriados += 1
        
        # Feriados NO trabajados: se suman a días laborados (derecho al feriado pagado)
        # Solo para trabajadores por hora, no guardas
        if not (hasattr(trabajador, 'tipo_pago') and trabajador.tipo_pago == 'por_turno'):
            feriados_no_trabajados = feriados_periodo - fechas_con_asistencia
            dias_laborados += len(feriados_no_trabajados)
        
        # ============================================================
        # 7. OBTENER SALARIO BASE DEL TRABAJADOR
        # ============================================================
        # Usar el salario más reciente del trabajador en el período
        ultima_asistencia = asistencias_trabajador.order_by('-fecha').first()
        
        # Día Base o Valor Turno según tipo de pago
        salario_hora = trabajador.salario_normal or Decimal('0.00')
        if hasattr(trabajador, 'tipo_pago') and trabajador.tipo_pago == 'por_turno':
            salario_dia_base = salario_hora  # Ya es el valor por turno
        else:
            salario_dia_base = (salario_hora * Decimal('8')).quantize(Decimal('0.01'))
        
        # ============================================================
        # 8. DETERMINAR ÁREA DEL TRABAJADOR
        # ============================================================
        # Clasificar según el puesto laboral
        puesto = trabajador.puesto_laboral.lower()
        
        if 'guarda' in puesto or 'celador' in puesto or 'vigilante' in puesto:
            area = 'guardas'
        elif any(word in puesto for word in ['secretaria', 'contador', 'gerente', 'administrador', 'analista']):
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
                bonos=trabajador.bonos or Decimal('0.00'),
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

def generar_planilla_administrativa(proyecto, periodo_inicio, periodo_fin, dias_periodo, usuario):
    """
    Genera planilla para personal administrativo.
    
    A diferencia de la planilla de construcción:
    - dias_periodo es input manual (no se calcula de asistencias)
    - Salario = salario_hora × 8 = día_base
    - 7mo día, vacaciones, aguinaldo, antigüedad se calculan automáticamente
    - Horas extras vienen de asistencias (>= 8.5h diarias)
    - Días feriados se detectan automáticamente
    
    Args:
        proyecto: Proyecto con is_administrativo=True
        periodo_inicio: fecha inicio del período
        periodo_fin: fecha fin del período  
        dias_periodo: días laborados del período (input manual, default 12)
        usuario: usuario que genera la planilla
    
    Returns:
        tuple: (planilla, detalles_list, errores_list)
    """
    errores = []
    
    # 1. Validaciones
    planilla_existente = Planilla.objects.filter(
        proyecto=proyecto,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        eliminado=False
    ).first()
    
    if planilla_existente:
        errores.append(f"Ya existe una planilla para este proyecto y período: {planilla_existente.codigo}")
        return None, [], errores
    
    # 2. Obtener trabajadores asignados al proyecto administrativo
    trabajadores = Trabajador.objects.filter(
        proyecto_asignado=proyecto,
        eliminado=False,
        estado='activo'
    ).order_by('area_cargo', 'apellido', 'nombre')
    
    if not trabajadores.exists():
        errores.append("No hay trabajadores activos asignados al proyecto administrativo")
        return None, [], errores
    
    # 3. Tipo de cambio
    tipo_cambio = TipoCambio.get_actual()
    
    # 4. Crear planilla
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
    
    # 5. Obtener días feriados en el período
    dias_feriados_periodo = DiaFeriado.objects.filter(
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin,
        activo=True
    ).values_list('fecha', flat=True)
    
    # 6. Generar detalle por trabajador
    detalles_list = []
    
    for trabajador in trabajadores:
        salario_hora = trabajador.salario_normal or Decimal('0.00')
        dia_base = salario_hora * Decimal('8')  # Día Base = salario_hora × 8
        
        # Horas extras del período (de asistencias, solo >= 8.5h diarias)
        horas_extras_total = Decimal('0.00')
        dias_feriados_trabajados = 0
        horas_en_feriados = Decimal('0.00')
        
        asistencias = Asistencia.objects.filter(
            trabajador=trabajador,
            proyecto=proyecto,
            fecha__gte=periodo_inicio,
            fecha__lte=periodo_fin,
            eliminado=False,
            estado='cerrado'
        )
        
        for asistencia in asistencias:
            horas_trabajadas = asistencia.horas_normales or Decimal('0.00')
            he = asistencia.horas_extras or Decimal('0.00')
            
            # Solo cuenta hora extra si >= 8.5h (8.1-8.4 NO cuenta)
            if horas_trabajadas >= Decimal('8.5'):
                horas_extras_total += he
            
            # Verificar si es día feriado
            if asistencia.fecha in dias_feriados_periodo:
                dias_feriados_trabajados += 1
                # Las horas trabajadas en feriado se pagan como hora extra
                horas_en_feriados += horas_trabajadas
        
        # Clasificar área
        puesto = trabajador.puesto_laboral.lower() if trabajador.puesto_laboral else ''
        if any(w in puesto for w in ['contador', 'gerente', 'administrador', 'asistente', 'secretaria']):
            area = 'administrativo'
        elif any(w in puesto for w in ['conductor', 'mensajero', 'conserje', 'auxiliar']):
            area = 'ayudantes'
        elif any(w in puesto for w in ['ingeniero', 'arquitecto', 'supervisor', 'fiscal']):
            area = 'oficiales'
        else:
            area = 'administrativo'
        
        # Crear detalle (el save() llamará calcular_valores_administrativo automáticamente)
        try:
            detalle = DetallePlanilla.objects.create(
                planilla=planilla,
                trabajador=trabajador,
                area=area,
                cargo=trabajador.puesto_laboral or '',
                dias_laborados=dias_periodo,
                horas_extras=horas_extras_total,
                dias_feriados=dias_feriados_trabajados,
                horas_feriado=horas_en_feriados,
                salario_dia_base=dia_base,
                bonos=trabajador.bonos or Decimal('0.00'),
            )
            detalles_list.append(detalle)
        except Exception as e:
            errores.append(f"Error con {trabajador.nombre_completo}: {str(e)}")
    
    # 7. Recalcular totales de la planilla
    if detalles_list:
        planilla.calcular_totales()
    
    return planilla, detalles_list, errores