from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def miles(value):
    """
    Formatea un número con separador de miles y 2 decimales.
    Uso: {{ monto|miles }}  →  1,250.00
    """
    try:
        num = float(value)
        if num == 0:
            return '0.00'
        return '{:,.2f}'.format(num)
    except (ValueError, TypeError):
        return value

@register.filter
def moneda(value):
    """
    Formatea como córdobas: C$ 1,250.00
    Uso: {{ monto|moneda }}
    """
    try:
        num = float(value)
        if num == 0:
            return 'C$ 0.00'
        return 'C$ {:,.2f}'.format(num)
    except (ValueError, TypeError):
        return value

@register.filter
def dolares(value):
    """
    Formatea como dólares: $ 1,250.00
    Uso: {{ monto|dolares }}
    """
    try:
        num = float(value)
        if num == 0:
            return '$ 0.00'
        return '$ {:,.2f}'.format(num)
    except (ValueError, TypeError):
        return value
        