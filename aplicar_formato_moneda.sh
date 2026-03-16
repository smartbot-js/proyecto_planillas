#!/bin/bash
# ============================================================
# Script para aplicar formato_moneda en todos los templates
# Ejecutar desde la raíz del proyecto: bash aplicar_formato_moneda.sh
# ============================================================

TEMPLATES_DIR="templates"

echo "============================================"
echo "1. Creando templatetag formato_moneda..."
echo "============================================"

mkdir -p apps/core/templatetags

# __init__.py
if [ ! -f apps/core/templatetags/__init__.py ]; then
    touch apps/core/templatetags/__init__.py
    echo "   ✅ __init__.py creado"
fi

# formato_moneda.py
cat > apps/core/templatetags/formato_moneda.py << 'PYEOF'
from django import template

register = template.Library()

@register.filter
def miles(value):
    """43695.91 → 43,695.91"""
    try:
        return '{:,.2f}'.format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def moneda(value):
    """43695.91 → C$ 43,695.91"""
    try:
        return 'C$ {:,.2f}'.format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def dolares(value):
    """1192.78 → $ 1,192.78"""
    try:
        return '$ {:,.2f}'.format(float(value))
    except (ValueError, TypeError):
        return value
PYEOF
echo "   ✅ formato_moneda.py creado"

echo ""
echo "============================================"
echo "2. Agregando {% load formato_moneda %} a templates..."
echo "============================================"

# Agregar {% load formato_moneda %} después de {% load static %} en todos los templates
# Solo si no existe ya
find "$TEMPLATES_DIR" -name "*.html" -type f | while read file; do
    # Verificar si ya tiene formato_moneda cargado
    if grep -q "load formato_moneda" "$file"; then
        continue
    fi
    
    # Verificar si tiene {% load static %}
    if grep -q "{% load static" "$file"; then
        # Agregar {% load formato_moneda %} en la línea siguiente al primer {% load static %}
        sed -i '/{% load static/a {% load formato_moneda %}' "$file"
        echo "   ✅ $file — agregado load"
    fi
done

echo ""
echo "============================================"
echo "3. Reemplazando C\$ {{ ...|floatformat:2 }} por {{ ...|moneda }}..."
echo "============================================"

# Patrón: C$ {{ variable|floatformat:2 }}  →  {{ variable|moneda }}
# Usar sed con regex
find "$TEMPLATES_DIR" -name "*.html" -type f | while read file; do
    # Contar matches antes
    count_before=$(grep -c 'C\$ {{ [^}]*|floatformat:2 }}' "$file" 2>/dev/null || echo 0)
    
    if [ "$count_before" -gt "0" ]; then
        # Reemplazar C$ {{ algo|floatformat:2 }} → {{ algo|moneda }}
        sed -i -E 's/C\$ \{\{ ([^|]+)\|floatformat:2 \}\}/{{ \1|moneda }}/g' "$file"
        echo "   ✅ $file — $count_before montos C$ corregidos"
    fi
done

echo ""
echo "============================================"
echo "4. Reemplazando \$ {{ ...|floatformat:2 }} por {{ ...|dolares }}..."
echo "============================================"

find "$TEMPLATES_DIR" -name "*.html" -type f | while read file; do
    # Patrón: $ {{ variable|floatformat:2 }} (sin C antes)
    # Cuidado: no capturar C$ (ya procesado arriba)
    count_before=$(grep -cP '(?<!C)\$ \{\{ [^}]*\|floatformat:2 \}\}' "$file" 2>/dev/null || echo 0)
    
    if [ "$count_before" -gt "0" ]; then
        sed -i -E 's/([^C])\$ \{\{ ([^|]+)\|floatformat:2 \}\}/\1{{ \2|dolares }}/g' "$file"
        # También al inicio de línea
        sed -i -E 's/^\$ \{\{ ([^|]+)\|floatformat:2 \}\}/{{ \1|dolares }}/g' "$file"
        echo "   ✅ $file — $count_before montos $ corregidos"
    fi
done

echo ""
echo "============================================"
echo "5. Casos especiales: montos sin prefijo C$/$ pero con floatformat:2 en contexto de dinero..."
echo "============================================"

# Estos son montos que están en columnas de dinero pero no tienen C$/$
# Por ejemplo: {{ detalle.ingreso_total|floatformat:2 }} dentro de una columna "Total C$"
# Estos los dejamos con floatformat:2 por ahora (el filtro miles se aplica manualmente)

echo "   ℹ️  Montos sin prefijo C$/$ se mantienen con floatformat:2"
echo "   ℹ️  Aplicar |miles manualmente si es necesario"

echo ""
echo "============================================"
echo "RESUMEN"
echo "============================================"

total_moneda=$(grep -r '|moneda' "$TEMPLATES_DIR" --include="*.html" | wc -l)
total_dolares=$(grep -r '|dolares' "$TEMPLATES_DIR" --include="*.html" | wc -l)
total_restantes=$(grep -r 'C\$ {{' "$TEMPLATES_DIR" --include="*.html" | grep 'floatformat:2' | wc -l)

echo "   Montos C$ formateados (|moneda): $total_moneda"
echo "   Montos $  formateados (|dolares): $total_dolares"
echo "   Montos C$ restantes sin formatear: $total_restantes"
echo ""
echo "✅ ¡Listo! Reinicia el servidor para que cargue el templatetag."