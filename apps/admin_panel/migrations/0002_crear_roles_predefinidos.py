from django.db import migrations

def crear_roles_iniciales(apps, schema_editor):
    Rol = apps.get_model('admin_panel', 'Rol')
    
    roles = [
        {
            'nombre': 'Asistencia',
            'codigo': 'asistencia',
            'descripcion': 'Rol para trabajadores - Solo app móvil para registrar asistencia',
            'es_sistema': True,
            'solo_app_movil': True,
            'alcance_proyectos': 'propio',
            'permisos': {
                'proyectos': {'ver': False, 'crear': False, 'editar': False, 'eliminar': False},
                'trabajadores': {'ver': False, 'crear': False, 'editar': False, 'eliminar': False},
                'asistencias': {'ver': True, 'crear': True, 'validar': False, 'corregir': False},
                'planillas': {'ver': False, 'crear': False, 'aprobar_gerente': False, 'aprobar_contador': False},
                'contratistas': {'ver': False, 'crear': False, 'editar': False, 'eliminar': False},
                'reportes': {'ver': False, 'exportar': False},
                'admin_panel': {'acceso': False}
            }
        },
        {
            'nombre': 'Residente / Maestro de Obra',
            'codigo': 'residente',
            'descripcion': 'Ve solo su proyecto, puede crear asistencias manuales',
            'es_sistema': True,
            'solo_app_movil': False,
            'alcance_proyectos': 'propio',
            'permisos': {
                'proyectos': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'trabajadores': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'asistencias': {'ver': True, 'crear': True, 'validar': False, 'corregir': False},
                'planillas': {'ver': True, 'crear': False, 'aprobar_gerente': False, 'aprobar_contador': False},
                'contratistas': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'reportes': {'ver': True, 'exportar': False},
                'admin_panel': {'acceso': False}
            }
        },
        {
            'nombre': 'Gerente de Proyecto',
            'codigo': 'gerente_proyecto',
            'descripcion': 'Ve solo sus proyectos asignados, revisa información',
            'es_sistema': True,
            'solo_app_movil': False,
            'alcance_proyectos': 'asignados',
            'permisos': {
                'proyectos': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'trabajadores': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'asistencias': {'ver': True, 'crear': False, 'validar': False, 'corregir': False},
                'planillas': {'ver': True, 'crear': False, 'aprobar_gerente': False, 'aprobar_contador': False},
                'contratistas': {'ver': True, 'crear': False, 'editar': False, 'eliminar': False},
                'reportes': {'ver': True, 'exportar': False},
                'admin_panel': {'acceso': False}
            }
        },
        {
            'nombre': 'Contador',
            'codigo': 'contador',
            'descripcion': 'Acceso completo, aprueba planillas como contador',
            'es_sistema': True,
            'solo_app_movil': False,
            'alcance_proyectos': 'todos',
            'permisos': {
                'proyectos': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'trabajadores': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'asistencias': {'ver': True, 'crear': True, 'validar': True, 'corregir': True},
                'planillas': {'ver': True, 'crear': True, 'aprobar_gerente': False, 'aprobar_contador': True},
                'contratistas': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'reportes': {'ver': True, 'exportar': True},
                'admin_panel': {'acceso': False}
            }
        },
        {
            'nombre': 'Gerente General',
            'codigo': 'gerente_general',
            'descripcion': 'Acceso completo, aprueba planillas como gerente',
            'es_sistema': True,
            'solo_app_movil': False,
            'alcance_proyectos': 'todos',
            'permisos': {
                'proyectos': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'trabajadores': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'asistencias': {'ver': True, 'crear': True, 'validar': True, 'corregir': True},
                'planillas': {'ver': True, 'crear': True, 'aprobar_gerente': True, 'aprobar_contador': False},
                'contratistas': {'ver': True, 'crear': True, 'editar': True, 'eliminar': False},
                'reportes': {'ver': True, 'exportar': True},
                'admin_panel': {'acceso': False}
            }
        },
        {
            'nombre': 'Administrador',
            'codigo': 'admin',
            'descripcion': 'Control total del sistema',
            'es_sistema': True,
            'solo_app_movil': False,
            'alcance_proyectos': 'todos',
            'permisos': {
                'proyectos': {'ver': True, 'crear': True, 'editar': True, 'eliminar': True},
                'trabajadores': {'ver': True, 'crear': True, 'editar': True, 'eliminar': True},
                'asistencias': {'ver': True, 'crear': True, 'validar': True, 'corregir': True},
                'planillas': {'ver': True, 'crear': True, 'aprobar_gerente': True, 'aprobar_contador': True},
                'contratistas': {'ver': True, 'crear': True, 'editar': True, 'eliminar': True},
                'reportes': {'ver': True, 'exportar': True},
                'admin_panel': {'acceso': True}
            }
        }
    ]
    
    for rol_data in roles:
        Rol.objects.create(**rol_data)

def revertir_roles(apps, schema_editor):
    Rol = apps.get_model('admin_panel', 'Rol')
    Rol.objects.filter(es_sistema=True).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('admin_panel', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(crear_roles_iniciales, revertir_roles),
    ]