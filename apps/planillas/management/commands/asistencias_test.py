"""
SCRIPT DE DIAGNÓSTICO - Verificar Asistencias
Ejecutar: python manage.py shell
Luego copiar y pegar este código
"""

from apps.asistencias.models import Asistencia
from apps.proyectos.models import Proyecto
from datetime import date

print("="*70)
print("DIAGNÓSTICO DE ASISTENCIAS - Proyecto Smartbot")
print("Período: 06/11/2025 - 18/11/2025")
print("="*70)

# Obtener proyecto
try:
    proyecto = Proyecto.objects.get(nombre='Smartbot')
    print(f"\n✅ Proyecto encontrado: {proyecto.nombre} (ID: {proyecto.id})")
except Proyecto.DoesNotExist:
    print("\n❌ Proyecto 'Smartbot' no encontrado")
    exit()

# Definir el rango de fechas que estás consultando
fecha_inicio = date(2025, 11, 6)
fecha_fin = date(2025, 11, 18)

print(f"\n📅 Buscando asistencias entre: {fecha_inicio} y {fecha_fin}")

# Buscar asistencias en ese rango
asistencias = Asistencia.objects.filter(
    proyecto=proyecto,
    fecha__gte=fecha_inicio,
    fecha__lte=fecha_fin
).order_by('fecha', 'trabajador__nombre')

print(f"\n📊 RESULTADOS:")
print(f"   Total asistencias: {asistencias.count()}")
print(f"   Validadas: {asistencias.filter(validado=True).count()}")
print(f"   No validadas: {asistencias.filter(validado=False).count()}")

if asistencias.count() > 0:
    print(f"\n{'='*70}")
    print("LISTADO DETALLADO DE ASISTENCIAS:")
    print(f"{'='*70}")
    
    for i, asist in enumerate(asistencias, 1):
        print(f"\n{i}. {asist.trabajador.nombre} {asist.trabajador.apellido}")
        print(f"   📅 Fecha: {asist.fecha} ({asist.fecha.strftime('%A')})")
        print(f"   🏗️  Proyecto: {asist.proyecto.nombre}")
        print(f"   ⏰ Estado: {asist.estado}")
        print(f"   ✅ Validado: {'Sí' if asist.validado else 'No'}")
        print(f"   ⌚ Horas normales: {asist.horas_normales}")
        print(f"   ⏱️  Horas extras: {asist.horas_extras}")
        print(f"   💰 Salario día: C$ {asist.salario_dia}")
        print(f"   🕐 Entrada: {asist.hora_entrada or 'No registrada'}")
        print(f"   🕐 Salida: {asist.hora_salida or 'No registrada'}")
        print(f"   🆔 ID: {asist.id}")
        
        # Detectar problemas
        problemas = []
        if asist.horas_normales == 0:
            problemas.append("⚠️  Horas normales en 0")
        if asist.salario_dia == 0:
            problemas.append("⚠️  Salario día en 0")
        if not asist.validado:
            problemas.append("⚠️  No validado")
        
        if problemas:
            print(f"   🔴 Problemas detectados:")
            for prob in problemas:
                print(f"      - {prob}")

else:
    print(f"\n✅ NO HAY ASISTENCIAS en ese rango de fechas")
    print(f"   Esto es correcto si no has registrado asistencias aún.")

# Buscar asistencias en OTRAS fechas del mismo proyecto
print(f"\n{'='*70}")
print("ASISTENCIAS EN OTROS PERÍODOS (Proyecto Smartbot):")
print(f"{'='*70}")

todas_asistencias = Asistencia.objects.filter(
    proyecto=proyecto
).order_by('-fecha')

if todas_asistencias.exists():
    print(f"\nTotal de asistencias del proyecto: {todas_asistencias.count()}")
    
    # Mostrar las primeras 10
    print(f"\nÚltimas 10 asistencias registradas:")
    for asist in todas_asistencias[:10]:
        print(f"   - {asist.fecha} | {asist.trabajador.nombre_completo} | Horas: {asist.horas_normales}")
    
    # Rango de fechas real
    fecha_min = todas_asistencias.last().fecha
    fecha_max = todas_asistencias.first().fecha
    print(f"\nRango de fechas con asistencias:")
    print(f"   Desde: {fecha_min}")
    print(f"   Hasta: {fecha_max}")
else:
    print("\n⚠️  Este proyecto NO tiene ninguna asistencia registrada")

print(f"\n{'='*70}")
print("FIN DEL DIAGNÓSTICO")
print(f"{'='*70}")