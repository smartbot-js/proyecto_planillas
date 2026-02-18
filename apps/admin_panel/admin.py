from django.contrib import admin
from .models import Rol

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'alcance_proyectos', 'es_sistema', 'activo', 'fecha_creacion']
    list_filter = ['es_sistema', 'activo', 'alcance_proyectos', 'solo_app_movil']
    search_fields = ['nombre', 'codigo', 'descripcion']
    readonly_fields = ['fecha_creacion', 'creado_por']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('alcance_proyectos', 'solo_app_movil', 'activo', 'es_sistema')
        }),
        ('Permisos', {
            'fields': ('permisos',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'creado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
        