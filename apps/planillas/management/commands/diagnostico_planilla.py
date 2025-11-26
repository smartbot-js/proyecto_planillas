"""
SCRIPT DE DIAGNÓSTICO - Planilla PL-PROY-2025-0006
Ejecutar en Django shell: python manage.py shell < diagnostico_planilla.py
"""

from apps.planillas.models import Planilla, DetallePlanilla
from apps.asistencias.models import Asistencia
from decimal import Decimal

# ============================================================
# 1. OBTENER LA PLANILLA PROBLEMÁTICA
# ============================================================
print("="*60)
print("DIAGNÓSTICO DE PLANILLA PL-PROY-2025-0006")
print("="*60)

try:
    planilla = Planilla.objects.get(codigo='PL-PROY-2025-0006')
    print(f"✅ Planilla encontrada: {planilla.codigo}")
    print(f"   - Estado: {planilla.estado}")
    print(f"   - Proyecto: {planilla.proyecto.nombre}")
    print(f"   - Período: {planilla.periodo_inicio} - {planilla.periodo_fin}")
    print(f"   - Total C$: {planilla.total_cordobas}")
    print(f"   - Total USD: {planilla.total_dolares}")
except Planilla.DoesNotExist:
    print("❌ ERROR: Planilla no encontrada")
    exit()

print("\n" + "="*60)
print("2. VERIFICAR DETALLES DE PLANILLA")
print("="*60)

detalles = DetallePlanilla.objects.filter(planilla=planilla)
print(f"Total de detalles: {detalles.count()}")

if detalles.count() == 0:
    print("❌ ERROR: NO HAY DETALLES!")
    print("   La planilla se creó pero no tiene trabajadores.")
    print("\n   POSIBLES CAUSAS:")
    print("   1. No hay asistencias validadas en el período")
    print("   2. Error al crear los detalles")
else:
    print(f"✅ Detalles encontrados: {detalles.count()}")
    
    print("\n" + "-"*60)
    print("DETALLE POR TRABAJADOR:")
    print("-"*60)
    
    for i, detalle in enumerate(detalles, 1):
        print(f"\n{i}. {detalle.trabajador.nombre} {detalle.trabajador.apellido}")
        print(f"   - Área: {detalle.get_area_display()}")
        print(f"   - Cargo: {detalle.cargo}")
        print(f"   - Días laborados: {detalle.dias_laborados}")
        print(f"   - Horas normales: {detalle.horas_normales}")
        print(f"   - Horas extras: {detalle.horas_extras}")
        print(f"   - Salario base: C$ {detalle.salario_dia_base}")
        print(f"   - Valor 7mo: C$ {detalle.valor_septimo_dia}")
        print(f"   - Salario + 7mo: C$ {detalle.salario_diario_con_septimo}")
        print(f"   - Salario devengado: C$ {detalle.salario_devengado}")
        print(f"   - Combustible: C$ {detalle.combustible}")
        print(f"   - Bonos: C$ {detalle.bonos}")
        print(f"   - Otros: C$ {detalle.otros_gastos}")
        print(f"   - INGRESO TOTAL: C$ {detalle.ingreso_total}")
        
        # Detectar problemas
        if detalle.ingreso_total == 0:
            print(f"   ⚠️  PROBLEMA: Ingreso total en CERO")
            if detalle.dias_laborados == 0:
                print(f"   ❌ Días laborados = 0")
            if detalle.salario_dia_base == 0:
                print(f"   ❌ Salario base = 0")

print("\n" + "="*60)
print("3. VERIFICAR ASISTENCIAS EN EL PERÍODO")
print("="*60)

asistencias = Asistencia.objects.filter(
    proyecto=planilla.proyecto,
    fecha__gte=planilla.periodo_inicio,
    fecha__lte=planilla.periodo_fin
)

print(f"Total asistencias: {asistencias.count()}")
print(f"Asistencias validadas: {asistencias.filter(validado=True).count()}")
print(f"Asistencias NO validadas: {asistencias.filter(validado=False).count()}")

if asistencias.filter(validado=True).exists():
    print("\n" + "-"*60)
    print("PRIMERAS 5 ASISTENCIAS VALIDADAS:")
    print("-"*60)
    
    for asist in asistencias.filter(validado=True)[:5]:
        print(f"\n- {asist.trabajador.nombre} {asist.trabajador.apellido}")
        print(f"  Fecha: {asist.fecha}")
        print(f"  Estado: {asist.estado}")
        print(f"  Horas normales: {asist.horas_normales}")
        print(f"  Horas extras: {asist.horas_extras}")
        print(f"  Salario día: C$ {asist.salario_dia}")
        
        if asist.horas_normales == 0:
            print(f"  ⚠️  PROBLEMA: Horas normales = 0")
        if asist.salario_dia == 0:
            print(f"  ⚠️  PROBLEMA: Salario día = 0")

print("\n" + "="*60)
print("4. RECALCULAR TOTALES")
print("="*60)

print("Intentando recalcular totales de la planilla...")
try:
    planilla.calcular_totales()
    planilla.refresh_from_db()
    print(f"✅ Totales recalculados:")
    print(f"   - Total C$: {planilla.total_cordobas}")
    print(f"   - Total USD: {planilla.total_dolares}")
except Exception as e:
    print(f"❌ ERROR al recalcular: {str(e)}")

print("\n" + "="*60)
print("5. DIAGNÓSTICO FINAL")
print("="*60)

# Resumen de problemas
problemas = []

if detalles.count() == 0:
    problemas.append("NO HAY DETALLES - La planilla está vacía")

if planilla.total_cordobas == 0:
    problemas.append("TOTAL EN CEROS")

detalles_sin_datos = detalles.filter(ingreso_total=0).count()
if detalles_sin_datos > 0:
    problemas.append(f"{detalles_sin_datos} detalles con ingreso = 0")

asist_sin_horas = asistencias.filter(validado=True, horas_normales=0).count()
if asist_sin_horas > 0:
    problemas.append(f"{asist_sin_horas} asistencias sin horas")

if problemas:
    print("❌ PROBLEMAS DETECTADOS:")
    for i, prob in enumerate(problemas, 1):
        print(f"   {i}. {prob}")
else:
    print("✅ No se detectaron problemas obvios")

print("\n" + "="*60)
print("RECOMENDACIONES:")
print("="*60)

if detalles.count() == 0:
    print("1. Elimina esta planilla y genera una nueva")
    print("2. Asegúrate de que haya asistencias validadas")
    
elif planilla.total_cordobas == 0 and detalles.count() > 0:
    print("1. Los detalles existen pero tienen valores en 0")
    print("2. Verifica que las asistencias tengan:")
    print("   - horas_normales > 0")
    print("   - salario_dia > 0")
    print("3. Puedes intentar recalcular manualmente:")
    print("   >>> from apps.planillas.models import DetallePlanilla")
    print("   >>> for d in DetallePlanilla.objects.filter(planilla=planilla):")
    print("   >>>     d.save()  # Esto recalcula automáticamente")

print("\n" + "="*60)
