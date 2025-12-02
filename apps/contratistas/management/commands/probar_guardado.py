from apps.proyectos.models import Proyecto
from apps.contratistas.models import Contratista
from apps.usuarios.models import Usuario

# Crear proyecto de prueba
supervisor = Usuario.objects.filter(rol='administrador').first()
proyecto = Proyecto.objects.create(
    nombre='Proyecto Prueba ManyToMany',
    ubicacion='Dirección de prueba',
    fecha_inicio='2025-01-01',
    supervisor=supervisor,
    creado_por=supervisor,
    modificado_por=supervisor,
    presupuesto_total=100000
)

# Asignar contratistas
contratista1 = Contratista.objects.first()
proyecto.contratistas.add(contratista1)

# Verificar
print(f"Contratistas del proyecto: {proyecto.contratistas.all()}")
print(f"Count: {proyecto.contratistas.count()}")

# Ver desde el contratista
print(f"Proyectos del contratista: {contratista1.proyectos_asignados.all()}")