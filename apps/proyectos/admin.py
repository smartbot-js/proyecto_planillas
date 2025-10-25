"""
Configuración del Django Admin para Proyectos
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    """
    Configuración personalizada del admin para Proyectos
    """
    
    list_display = (
        'nombre',
        'ubicacion',
        'supervisor',
        'estado_badge',
        'presupuesto_info',
        'fecha_inicio',
        'dias_info',
    )
    
    list_filter = (
        'estado',
        'fecha_inicio',
        'supervisor',
    )
    
    search_fields = (
        'nombre',
        'descripcion',
        'ubicacion',
        'supervisor__nombre_completo',
    )
    
    ordering = ('-fecha_creacion',)
    
    readonly_fields = (
        'fecha_creacion',
        'fecha_actualizacion',
        'presupuesto_disponible_display',
        'porcentaje_gastado_display',
        'dias_transcurridos_display',
    )
    
    fieldsets = (
        (_('Información Básica'), {
            'fields': (
                'nombre',
                'descripcion',
                'ubicacion',
                'supervisor',
            )
        }),
        (_('Fechas'), {
            'fields': (
                'fecha_inicio',
                'fecha_fin_estimada',
                'fecha_fin_real',
            )
        }),
        (_('Estado y Presupuesto'), {
            'fields': (
                'estado',
                'presupuesto',
                'presupuesto_gastado',
                'presupuesto_disponible_display',
                'porcentaje_gastado_display',
            )
        }),
        (_('Información del Sistema'), {
            'fields': (
                'fecha_creacion',
                'fecha_actualizacion',
                'dias_transcurridos_display',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activar_proyectos', 'pausar_proyectos', 'finalizar_proyectos']
    
    def estado_badge(self, obj):
        """Muestra el estado con color"""
        colors = {
            'activo': '#10b981',
            'pausado': '#f59e0b',
            'finalizado': '#6b7280',
            'cancelado': '#ef4444',
        }
        color = colors.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px; font-weight: 600;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = _('Estado')
    
    def presupuesto_info(self, obj):
        """Muestra información del presupuesto"""
        porcentaje = obj.porcentaje_gastado()
        color = '#10b981' if porcentaje < 70 else '#f59e0b' if porcentaje < 90 else '#ef4444'
        return format_html(
            '<div style="font-size: 12px;">'
            '<strong>${:,.2f}</strong> / ${:,.2f}<br>'
            '<span style="color: {};">{:.1f}% gastado</span>'
            '</div>',
            obj.presupuesto_gastado,
            obj.presupuesto,
            color,
            porcentaje
        )
    presupuesto_info.short_description = _('Presupuesto')
    
    def dias_info(self, obj):
        """Muestra información de días"""
        transcurridos = obj.dias_transcurridos()
        restantes = obj.dias_restantes()
        return format_html(
            '<div style="font-size: 12px;">'
            '<strong>{}</strong> días transcurridos<br>'
            '<span style="color: #6b7280;">{} días restantes</span>'
            '</div>',
            transcurridos,
            restantes if restantes > 0 else '---'
        )
    dias_info.short_description = _('Duración')
    
    def presupuesto_disponible_display(self, obj):
        """Muestra el presupuesto disponible"""
        return f"${obj.presupuesto_disponible():,.2f}"
    presupuesto_disponible_display.short_description = _('Presupuesto Disponible')
    
    def porcentaje_gastado_display(self, obj):
        """Muestra el porcentaje gastado"""
        return f"{obj.porcentaje_gastado():.2f}%"
    porcentaje_gastado_display.short_description = _('Porcentaje Gastado')
    
    def dias_transcurridos_display(self, obj):
        """Muestra los días transcurridos"""
        return f"{obj.dias_transcurridos()} días"
    dias_transcurridos_display.short_description = _('Días Transcurridos')
    
    # Acciones personalizadas
    def activar_proyectos(self, request, queryset):
        """Activa los proyectos seleccionados"""
        actualizados = queryset.update(estado=Proyecto.Estado.ACTIVO)
        self.message_user(request, f'{actualizados} proyecto(s) activado(s).')
    activar_proyectos.short_description = _('Activar proyectos seleccionados')
    
    def pausar_proyectos(self, request, queryset):
        """Pausa los proyectos seleccionados"""
        actualizados = queryset.update(estado=Proyecto.Estado.PAUSADO)
        self.message_user(request, f'{actualizados} proyecto(s) pausado(s).')
    pausar_proyectos.short_description = _('Pausar proyectos seleccionados')
    
    def finalizar_proyectos(self, request, queryset):
        """Finaliza los proyectos seleccionados"""
        from django.utils import timezone
        actualizados = 0
        for proyecto in queryset:
            proyecto.estado = Proyecto.Estado.FINALIZADO
            if not proyecto.fecha_fin_real:
                proyecto.fecha_fin_real = timezone.now().date()
            proyecto.save()
            actualizados += 1
        self.message_user(request, f'{actualizados} proyecto(s) finalizado(s).')
    finalizar_proyectos.short_description = _('Finalizar proyectos seleccionados')

