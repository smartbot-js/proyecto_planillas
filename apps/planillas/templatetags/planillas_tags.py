"""
Template tags personalizados para el módulo de planillas
apps/planillas/templatetags/planillas_tags.py
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario por su clave
    Uso en template: {{ mi_dict|get_item:clave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """
    Multiplica un valor por un argumento
    Uso: {{ valor|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, arg):
    """
    Calcula el porcentaje de un valor
    Uso: {{ valor|percentage:19 }} para 19%
    """
    try:
        return float(value) * (float(arg) / 100)
    except (ValueError, TypeError):
        return 0
    