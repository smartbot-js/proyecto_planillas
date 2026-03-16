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
