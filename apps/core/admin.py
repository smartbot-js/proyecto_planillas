"""
Configuración del Admin para Core
apps/core/admin.py
"""
from django.contrib import admin
from .models import ConfiguracionSistema, HistorialTipoCambio


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    """Admin para configuración global del sistema"""
    
    # Solo mostrar los campos editables
    fields = ['tipo_cambio_actual', 'nombre_empresa', 'actualizado_en']
    readonly_fields = ['actualizado_en']
    
    def has_add_permission(self, request):
        # Solo puede existir UN registro
        try:
            return not ConfiguracionSistema.objects.exists()
        except:
            return True
    
    def has_delete_permission(self, request, obj=None):
        # No se puede eliminar
        return False
    
    def changelist_view(self, request, extra_context=None):
        # Si no existe, crear automáticamente
        if not ConfiguracionSistema.objects.exists():
            ConfiguracionSistema.objects.create()
        
        # Redirigir directamente al único registro
        obj = ConfiguracionSistema.get_configuracion()
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse('admin:core_configuracionsistema_change', args=[obj.pk]))


@admin.register(HistorialTipoCambio)
class HistorialTipoCambioAdmin(admin.ModelAdmin):
    """Admin para historial de tipo de cambio"""
    
    list_display = ['tipo_cambio', 'fecha_cambio', 'observaciones_cortas']
    list_filter = ['fecha_cambio']
    search_fields = ['tipo_cambio', 'observaciones']
    readonly_fields = ['tipo_cambio', 'fecha_cambio']
    date_hierarchy = 'fecha_cambio'
    
    def observaciones_cortas(self, obj):
        if obj.observaciones:
            return obj.observaciones[:50] + '...' if len(obj.observaciones) > 50 else obj.observaciones
        return '-'
    observaciones_cortas.short_description = 'Observaciones'
    
    def has_add_permission(self, request):
        # No se puede agregar manualmente, se crea automáticamente
        return False
    
    def has_delete_permission(self, request, obj=None):
        # No se puede eliminar el historial
        return False