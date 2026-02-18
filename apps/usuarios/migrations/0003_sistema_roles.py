from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone

def migrar_roles_antiguos(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')
    Rol = apps.get_model('admin_panel', 'Rol')
    
    # Obtener rol admin
    try:
        rol_admin = Rol.objects.get(codigo='admin')
    except Rol.DoesNotExist:
        return
    
    # Asignar rol admin a superusers y aprobarlos
    for usuario in Usuario.objects.filter(is_superuser=True):
        usuario.rol_nuevo = rol_admin
        usuario.cuenta_aprobada = True
        usuario.fecha_aprobacion = timezone.now()
        usuario.save()

class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0002_alter_usuario_rol'),
        ('admin_panel', '0002_crear_roles_predefinidos'),
    ]
    
    operations = [
        # Renombrar campo rol antiguo
        migrations.RenameField(
            model_name='usuario',
            old_name='rol',
            new_name='rol_legacy',
        ),
        # Crear nuevo campo rol como FK temporal
        migrations.AddField(
            model_name='usuario',
            name='rol_nuevo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='usuarios_temp',
                to='admin_panel.rol',
                verbose_name='Rol Nuevo'
            ),
        ),
        # Campos de aprobación
        migrations.AddField(
            model_name='usuario',
            name='cuenta_aprobada',
            field=models.BooleanField(default=False, verbose_name='Cuenta Aprobada'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='aprobada_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='cuentas_que_aprobo',
                to='usuarios.usuario',
                verbose_name='Aprobada por'
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='fecha_aprobacion',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Aprobación'),
        ),
        # Migrar datos
        migrations.RunPython(migrar_roles_antiguos, migrations.RunPython.noop),
        # Eliminar campo legacy
        migrations.RemoveField(
            model_name='usuario',
            name='rol_legacy',
        ),
        # Renombrar rol_nuevo a rol
        migrations.RenameField(
            model_name='usuario',
            old_name='rol_nuevo',
            new_name='rol',
        ),
    ]