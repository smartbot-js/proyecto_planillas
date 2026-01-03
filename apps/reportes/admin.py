"""
Administración del módulo de Reportes
apps/reportes/admin.py
"""
from django.contrib import admin
from .models import ConfiguracionEmpresa


@admin.register(ConfiguracionEmpresa)
class ConfiguracionEmpresaAdmin(admin.ModelAdmin):
    """
    Administración de Configuración de Empresa
    """
    list_display = ['nombre_empresa', 'ruc', 'activo', 'fecha_actualizacion']
    list_filter = ['activo']
    search_fields = ['nombre_empresa', 'ruc']
    
    fieldsets = (
        ('Información General', {
            'fields': ('nombre_empresa', 'logo_empresa', 'ruc')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email')
        }),
        ('Configuración Financiera', {
            'fields': ('tipo_cambio_default',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """
        No permitir eliminar la configuración principal
        """
        if obj and obj.activo:
            return False
        return super().has_delete_permission(request, obj)
        