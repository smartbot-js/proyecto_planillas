# Script SIMPLE - Solo campos que existen
exec(open('poblar_datos_prueba.py', encoding='utf-8').read())

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from apps.usuarios.models import Usuario
from apps.proyectos.models import Proyecto
from apps.trabajadores.models import Trabajador
from apps.asistencias.models import Asistencia
from apps.planillas.models import Planilla, DetallePlanilla
from apps.contratistas.models import Contratista, ContratoProyecto, AvaluoContratista, PlanillaContratista, DetallePlanillaContratista
from apps.reportes.models import ConfiguracionEmpresa

print("CREANDO DATOS...")

# 1. Config
config, _ = ConfiguracionEmpresa.objects.get_or_create(activo=True, defaults={'nombre_empresa': 'QUADYCONS', 'tipo_cambio_default': Decimal('36.60')})
print("OK - Config")

# 2. Usuarios
usuarios = []
for email, nombre, rol in [('gerente@test.com', 'Carlos Gerente', 'gerente'), ('contador@test.com', 'Maria Contador', 'contador')]:
    u, _ = Usuario.objects.get_or_create(email=email, defaults={'nombre_completo': nombre, 'rol': rol})
    if _: u.set_password('pass123'); u.save()
    usuarios.append(u)
print(f"OK - {len(usuarios)} usuarios")

# 3. Proyectos - SOLO CAMPOS QUE EXISTEN
proyectos = []
for i, nombre in enumerate(['Edificio Torres del Sol', 'Centro Comercial Norte'], 1):
    p, _ = Proyecto.objects.get_or_create(
        nombre=nombre,
        defaults={
            'descripcion': f'Proyecto {nombre}',
            'fecha_inicio': timezone.now().date() - timedelta(days=60),
            'supervisor': usuarios[0],
            'presupuesto_total': Decimal(2000000),
        }
    )
    proyectos.append(p)
print(f"OK - {len(proyectos)} proyectos")

# 4. Trabajadores
trabajadores = []
for i in range(1, 11):
    t, _ = Trabajador.objects.get_or_create(
        numero_inss=f'INSS-{1000+i}',
        defaults={
            'nombre_completo': f'Trabajador {i}',
            'numero_cedula': f'001-{150000+i:06d}-0001K',
            'cargo': 'Oficial' if i <= 5 else 'Ayudante',
            'salario_base_cordobas': Decimal(random.randint(10000, 20000)),
            'fecha_ingreso': timezone.now().date() - timedelta(days=100),
            'estado': 'activo',
            'proyecto': random.choice(proyectos),
        }
    )
    trabajadores.append(t)
print(f"OK - {len(trabajadores)} trabajadores")

# 5. Planillas
for proyecto in proyectos:
    fecha_inicio = timezone.now().date().replace(day=1) - timedelta(days=30)
    fecha_fin = fecha_inicio + timedelta(days=25)
    
    planilla, created = Planilla.objects.get_or_create(
        proyecto=proyecto,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        defaults={
            'fecha_generacion': timezone.now().date(),
            'codigo_planilla': f'PL-{proyecto.id:03d}-test',
            'periodo_texto': f'Periodo {fecha_inicio} a {fecha_fin}',
            'estado': 'pagada',
            'aprobado_gerente': True,
            'aprobado_contador': True,
        }
    )
    
    if created:
        trabajadores_proy = Trabajador.objects.filter(proyecto=proyecto)
        total = Decimal('0.00')
        for t in trabajadores_proy:
            DetallePlanilla.objects.create(
                planilla=planilla,
                trabajador=t,
                dias_trabajados=random.randint(20, 26),
                salario_base_cordobas=t.salario_base_cordobas,
                total_pago_cordobas=t.salario_base_cordobas,
            )
            total += t.salario_base_cordobas
        planilla.total_cordobas = total
        planilla.save()
print("OK - Planillas")

# 6. Contratistas
contratistas = []
for i, nombre in enumerate(['Constructora ABC', 'Ing. Manuel Rodriguez'], 1):
    c, _ = Contratista.objects.get_or_create(
        nombre_completo=nombre,
        defaults={'tipo': 'juridica' if 'Constructora' in nombre else 'natural'}
    )
    contratistas.append(c)
    
    # Contrato
    contrato, created = ContratoProyecto.objects.get_or_create(
        contratista=c,
        proyecto=proyectos[0],
        numero_contrato=f'CONT-{i:03d}',
        defaults={
            'descripcion': f'Contrato {nombre}',
            'monto_total_cordobas': Decimal(100000),
            'fecha_inicio': timezone.now().date() - timedelta(days=50),
            'fecha_fin': timezone.now().date() + timedelta(days=100),
            'estado': 'activo',
        }
    )
    
    if created:
        # Avaluo
        AvaluoContratista.objects.create(
            contrato=contrato,
            numero_avaluo=f'AV-{i:03d}',
            fecha_avaluo=timezone.now().date() - timedelta(days=20),
            descripcion_trabajo='Avance de obra',
            monto_cordobas=Decimal(30000),
            estado='aprobado_contador',
            aprobado_gerente=True,
            aprobado_contador=True,
        )

print(f"OK - {len(contratistas)} contratistas")

print("\n" + "="*50)
print(f"Proyectos: {Proyecto.objects.count()}")
print(f"Trabajadores: {Trabajador.objects.count()}")
print(f"Planillas: {Planilla.objects.count()}")
print(f"Contratistas: {Contratista.objects.count()}")
print("="*50)
print("\nLISTO! Prueba /reportes/proyecto/")