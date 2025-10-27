from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'presupuesto_info',
    )
    search_fields = ('nombre',)
    list_filter = ()
    readonly_fields = ()
    list_editable = ()

    def presupuesto_info(self, obj):
        """Muestra información del presupuesto de forma segura en el admin."""
        def safe_float(value):
            """Convierte a float de forma segura, sin romper si es string o SafeString."""
            try:
                return float(str(value).replace('$', '').replace(',', '').strip())
            except Exception:
                return 0.0

        gastado = safe_float(getattr(obj, 'presupuesto_gastado', lambda: 0)())
        total = safe_float(getattr(obj, 'presupuesto_total', 0))
        porcentaje = safe_float(getattr(obj, 'porcentaje_gastado', lambda: 0)())

        # Aseguramos que el porcentaje no supere 100 ni sea negativo
        porcentaje = max(0, min(porcentaje, 100))

        # Colores según el porcentaje
        if porcentaje < 70:
            color = '#10b981'   # verde
        elif porcentaje < 90:
            color = '#f59e0b'   # amarillo
        else:
            color = '#ef4444'   # rojo

        # 🔹 Formateamos los números antes de insertarlos en el HTML
        gastado_fmt = f"${gastado:,.2f}"
        total_fmt = f"${total:,.2f}"
        porcentaje_fmt = f"{porcentaje:.1f}%"

        return format_html(
            '<div style="font-size: 12px;">'
            '<strong>{}</strong> / {}<br>'
            '<span style="color: {};">{} gastado</span>'
            '</div>',
            gastado_fmt,
            total_fmt,
            color,
            porcentaje_fmt
        )

    def has_delete_permission(self, request, obj=None):
        return True
