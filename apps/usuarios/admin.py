"""
Configuración del Django Admin para Usuarios
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """
    Configuración personalizada del admin para el modelo Usuario
    """

    # Campos a mostrar en la lista de usuarios
    list_display = (
        'email',
        'nombre_completo',
        'rol',
        'activo',
        'is_staff',
        'fecha_creacion',
    )

    # Campos por los que se puede filtrar
    list_filter = (
        'rol',
        'activo',
        'is_staff',
        'is_superuser',
        'fecha_creacion',
    )

    # Campos por los que se puede buscar
    search_fields = (
        'email',
        'nombre_completo',
    )

    # Orden por defecto
    ordering = ('-fecha_creacion',)

    # Campos de solo lectura
    readonly_fields = (
        'fecha_creacion',
        'fecha_actualizacion',
        'last_login',
    )

    # Configuración de los fieldsets (secciones del formulario)
    fieldsets = (
        (_('Información de Autenticación'), {
            'fields': ('email', 'password')
        }),
        (_('Información Personal'), {
            'fields': ('nombre_completo', 'rol')
        }),
        (_('Permisos'), {
            'fields': (
                'activo',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Fechas Importantes'), {
            'fields': ('last_login', 'fecha_creacion', 'fecha_actualizacion'),
        }),
    )

    # Configuración de los fieldsets para agregar nuevo usuario
    add_fieldsets = (
        (_('Información de Autenticación'), {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Información Personal'), {
            'classes': ('wide',),
            'fields': ('nombre_completo', 'rol'),
        }),
        (_('Permisos'), {
            'classes': ('wide',),
            'fields': ('activo', 'is_staff', 'is_superuser'),
        }),
    )

    # Acciones personalizadas
    actions = ['activar_usuarios', 'desactivar_usuarios']

    def activar_usuarios(self, request, queryset):
        """Acción para activar usuarios seleccionados"""
        actualizados = queryset.update(activo=True)
        self.message_user(
            request,
            f'{actualizados} usuario(s) activado(s) correctamente.'
        )
    activar_usuarios.short_description = _('Activar usuarios seleccionados')

    def desactivar_usuarios(self, request, queryset):
        """Acción para desactivar usuarios seleccionados"""
        actualizados = queryset.update(activo=False)
        self.message_user(
            request,
            f'{actualizados} usuario(s) desactivado(s) correctamente.'
        )
    desactivar_usuarios.short_description = _('Desactivar usuarios seleccionados')