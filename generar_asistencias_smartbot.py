"""
Script para generar asistencias de prueba para el proyecto Smartbot
Ejecutar con: python manage.py shell < generar_asistencias_smartbot.py
O copiar y pegar en: python manage.py shell
"""

from apps.asistencias.models import Asistencia
from apps.trabajadores.models import Trabajador
from apps.proyectos.models import Proyecto
from datetime import date, time, timedelta
from decimal import Decimal
import random

print("=" * 70)
print("GENERANDO ASISTENCIAS DE PRUEBA PARA PROYECTO SMARTBOT")
print("=" * 70)

# ============================================================
# 1. OBTENER PROYECTO SMARTBOT
# ============================================================
try:
    proyecto = Proyecto.objects.get(id=4)
    print(f"\n✅ Proyecto encontrado: {proyecto.nombre}")
except Proyecto.DoesNotExist:
    print("\n❌ Error: No se encontró el proyecto con ID 4")
    print("   Verifica que el proyecto Smartbot exista")
    exit()

# ============================================================
# 2. OBTENER TRABAJADORES DEL PROYECTO
# ============================================================
trabajadores = Trabajador.objects.filter(
    proyecto_asignado=proyecto,
    estado='activo'
)

if not trabajadores.exists():
    print("\n⚠️  No hay trabajadores asignados al proyecto Smartbot")
    print("   Buscando trabajadores activos en cualquier proyecto...")
    
    # Buscar trabajadores activos de cualquier proyecto
    trabajadores = Trabajador.objects.filter(estado='activo')
    
    if not trabajadores.exists():
        print("\n❌ Error: No hay trabajadores activos en el sistema")
        print("   Crea trabajadores primero desde /trabajadores/crear/")
        exit()
    
    # Tomar los primeros 5 trabajadores
    trabajadores = list(trabajadores[:5])
    print(f"   Se usarán {len(trabajadores)} trabajadores disponibles")
else:
    trabajadores = list(trabajadores)

print(f"✅ Trabajadores encontrados: {len(trabajadores)}")
for t in trabajadores:
    print(f"   • {t.nombre_completo} ({t.puesto_laboral})")

# ============================================================
# 3. DEFINIR PERÍODO (ÚLTIMA CATORCENA)
# ============================================================
# Período: Jueves 31 de Octubre al Martes 12 de Noviembre (13 días)
fecha_inicio = date(2025, 10, 31)  # Jueves
fecha_fin = date(2025, 11, 12)     # Martes (13 días después)

print(f"\n📅 Período de asistencias:")
print(f"   Inicio: {fecha_inicio.strftime('%d/%m/%Y')} ({['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][fecha_inicio.weekday()]})")
print(f"   Fin: {fecha_fin.strftime('%d/%m/%Y')} ({['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][fecha_fin.weekday()]})")
print(f"   Total días: {(fecha_fin - fecha_inicio).days + 1}")

# ============================================================
# 4. ELIMINAR ASISTENCIAS EXISTENTES DEL PERÍODO
# ============================================================
asistencias_existentes = Asistencia.objects.filter(
    proyecto=proyecto,
    fecha__gte=fecha_inicio,
    fecha__lte=fecha_fin
)

if asistencias_existentes.exists():
    cantidad = asistencias_existentes.count()
    asistencias_existentes.delete()
    print(f"\n🗑️  Se eliminaron {cantidad} asistencias existentes del período")

# ============================================================
# 5. GENERAR ASISTENCIAS
# ============================================================
print(f"\n🔄 Generando asistencias...")

asistencias_creadas = 0
fecha_actual = fecha_inicio

# Salarios base por tipo de trabajador
salarios_base = {
    'albañil': Decimal('400.00'),
    'maestro': Decimal('500.00'),
    'ayudante': Decimal('300.00'),
    'oficial': Decimal('450.00'),
    'fontanero': Decimal('450.00'),
    'electricista': Decimal('450.00'),
    'bodeguero': Decimal('350.00'),
    'guarda': Decimal('320.00'),
    'default': Decimal('350.00')
}

while fecha_actual <= fecha_fin:
    dia_semana = fecha_actual.weekday()  # 0=Lunes, 6=Domingo
    dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][dia_semana]
    
    # Saltar domingos (los albañiles no trabajan domingos)
    if dia_semana == 6:
        print(f"   ⏭️  {fecha_actual.strftime('%d/%m/%Y')} ({dia_nombre}) - SALTADO (Domingo)")
        fecha_actual += timedelta(days=1)
        continue
    
    print(f"   📅 {fecha_actual.strftime('%d/%m/%Y')} ({dia_nombre}):")
    
    # Crear asistencias para cada trabajador
    for trabajador in trabajadores:
        # Determinar salario base según puesto
        puesto_lower = trabajador.puesto_laboral.lower()
        salario_dia = salarios_base.get('default')
        
        for key, valor in salarios_base.items():
            if key in puesto_lower:
                salario_dia = valor
                break
        
        # Horas trabajadas normales (8 horas por día)
        horas_trabajadas = Decimal('8.00')
        
        # Probabilidad de horas extras (30% de probabilidad)
        horas_extras = Decimal('0.00')
        if random.random() < 0.3:
            horas_extras = Decimal(str(random.choice([1.0, 2.0, 3.0])))
        
        # Probabilidad de faltar (5% de probabilidad)
        if random.random() < 0.05:
            print(f"      ⭕ {trabajador.nombre_completo} - AUSENTE")
            continue
        
        # Crear asistencia
        asistencia = Asistencia.objects.create(
            trabajador=trabajador,
            proyecto=proyecto,
            fecha=fecha_actual,
            puesto_laboral=trabajador.puesto_laboral,
            
            # Salarios
            salario_dia=salario_dia,
            tarifa_hora_extra=(salario_dia / Decimal('12')) * Decimal('2'),
            
            # Horarios
            hora_entrada=time(7, 0),
            hora_salida=time(16, 0) if horas_extras == 0 else time(17 + int(horas_extras), 0),
            
            # Horas
            horas_trabajadas=horas_trabajadas,
            horas_extras=horas_extras,
            
            # Estado
            estado='cerrado',  # Turno cerrado
            validado=True,     # ✅ IMPORTANTE: Ya validado
            
            # Método
            metodo_registro='manual'
        )
        
        asistencias_creadas += 1
        
        if horas_extras > 0:
            print(f"      ✅ {trabajador.nombre_completo} - {horas_trabajadas}h + {horas_extras}h extras")
        else:
            print(f"      ✅ {trabajador.nombre_completo} - {horas_trabajadas}h")
    
    fecha_actual += timedelta(days=1)

# ============================================================
# 6. RESUMEN FINAL
# ============================================================
print("\n" + "=" * 70)
print("✅ ASISTENCIAS GENERADAS EXITOSAMENTE")
print("=" * 70)

print(f"\n📊 RESUMEN:")
print(f"   • Proyecto: {proyecto.nombre}")
print(f"   • Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
print(f"   • Trabajadores: {len(trabajadores)}")
print(f"   • Asistencias creadas: {asistencias_creadas}")

# Calcular totales
total_horas = Asistencia.objects.filter(
    proyecto=proyecto,
    fecha__gte=fecha_inicio,
    fecha__lte=fecha_fin
).aggregate(
    horas=models.Sum('horas_trabajadas'),
    extras=models.Sum('horas_extras')
)

print(f"   • Total horas normales: {float(total_horas['horas'] or 0)}")
print(f"   • Total horas extras: {float(total_horas['extras'] or 0)}")

print("\n🎯 PRÓXIMOS PASOS:")
print("   1. Ve a: http://localhost:8000/planillas/crear/")
print("   2. Selecciona el proyecto: Smartbot")
print(f"   3. Período inicio: {fecha_inicio.strftime('%Y-%m-%d')}")
print(f"   4. Período fin: {fecha_fin.strftime('%Y-%m-%d')}")
print("   5. Click en 'Ver Preview'")
print("   6. Verifica los cálculos y genera la planilla")

print("\n" + "=" * 70)