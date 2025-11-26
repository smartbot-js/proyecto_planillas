"""
SCRIPT - Verificar y Limpiar Planillas Eliminadas
Ejecutar: python manage.py shell
"""

from apps.planillas.models import Planilla
from datetime import date

print("="*70)
print("VERIFICACIÓN DE PLANILLAS - Proyecto Smartbot")
print("="*70)

# Buscar todas las planillas (incluso eliminadas)
planillas_smartbot = Planilla.objects.filter(
    proyecto__nombre='Smartbot'
).order_by('-fecha_generacion')

print(f"\nTotal planillas (incluyendo eliminadas): {planillas_smartbot.count()}")

# Planillas activas
activas = planillas_smartbot.filter(eliminado=False)
print(f"Planillas activas: {activas.count()}")

# Planillas eliminadas (soft delete)
eliminadas = planillas_smartbot.filter(eliminado=True)
print(f"Planillas eliminadas (soft delete): {eliminadas.count()}")

print(f"\n{'='*70}")
print("LISTADO DE TODAS LAS PLANILLAS:")
print(f"{'='*70}")

for p in planillas_smartbot:
    estado_text = "🗑️ ELIMINADA" if p.eliminado else f"✅ {p.get_estado_display().upper()}"
    print(f"\n{p.codigo} - {estado_text}")
    print(f"   Período: {p.periodo_inicio} - {p.periodo_fin}")
    print(f"   Total: C$ {p.total_cordobas}")
    print(f"   ID: {p.pk}")
    print(f"   Eliminado: {p.eliminado}")

# Buscar planillas duplicadas en el rango problemático
print(f"\n{'='*70}")
print("PLANILLAS EN EL PERÍODO PROBLEMÁTICO (06/11 - 18/11):")
print(f"{'='*70}")

fecha_inicio = date(2025, 11, 6)
fecha_fin = date(2025, 11, 18)

duplicadas = Planilla.objects.filter(
    proyecto__nombre='Smartbot',
    periodo_inicio=fecha_inicio,
    periodo_fin=fecha_fin
).order_by('eliminado', '-fecha_generacion')

print(f"\nPlanillas encontradas: {duplicadas.count()}")

if duplicadas.count() > 0:
    for p in duplicadas:
        estado = "🗑️ ELIMINADA (SOFT DELETE)" if p.eliminado else f"✅ ACTIVA - {p.get_estado_display()}"
        print(f"\n{p.codigo} - {estado}")
        print(f"   ID: {p.pk}")
        print(f"   Total: C$ {p.total_cordobas}")
        print(f"   Detalles: {p.detalles.count()} trabajadores")
        
        if p.eliminado:
            print(f"   ⚠️  ESTA PLANILLA ESTÁ BLOQUEANDO LA CREACIÓN DE UNA NUEVA")

print(f"\n{'='*70}")
print("SOLUCIONES:")
print(f"{'='*70}")

if duplicadas.filter(eliminado=True).exists():
    print("\n❌ PROBLEMA DETECTADO:")
    print("   Hay planilla(s) eliminada(s) con soft delete que bloquean la creación.")
    print("\n✅ SOLUCIÓN 1 - Eliminar físicamente (Recomendado):")
    print("   Ejecuta este código:")
    print("")
    print("   # Eliminar físicamente las planillas en soft delete")
    print(f"   from apps.planillas.models import Planilla")
    print(f"   from datetime import date")
    print(f"   Planilla.objects.filter(")
    print(f"       proyecto__nombre='Smartbot',")
    print(f"       periodo_inicio=date(2025, 11, 6),")
    print(f"       periodo_fin=date(2025, 11, 18),")
    print(f"       eliminado=True")
    print(f"   ).delete()  # Esto elimina FÍSICAMENTE")
    print(f"   print('✅ Planillas eliminadas físicamente')")
    print("")
    print("\n✅ SOLUCIÓN 2 - Cambiar fechas:")
    print("   Usa otro rango de fechas diferente.")
    print("")
    print("\n✅ SOLUCIÓN 3 - Modificar el modelo (largo plazo):")
    print("   Agregar 'eliminado' al unique_together o usar UniqueConstraint")
    
elif duplicadas.filter(eliminado=False).exists():
    print("\n⚠️  Hay planilla(s) activa(s) en ese período.")
    print("   No puedes crear otra planilla con las mismas fechas.")
    print("\n   OPCIONES:")
    print("   1. Usa las planillas existentes")
    print("   2. Elimínalas desde la web")
    print("   3. Cambia las fechas")
else:
    print("\n✅ No hay planillas en ese período")
    print("   Deberías poder crear una nueva sin problemas")

print(f"\n{'='*70}")
print("FIN DEL DIAGNÓSTICO")
print(f"{'='*70}")