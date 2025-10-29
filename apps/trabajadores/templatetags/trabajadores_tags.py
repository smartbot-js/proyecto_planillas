"""
Template tags personalizados para trabajadores
"""
from django import template

register = template.Library()


@register.filter(name='format_cedula')
def format_cedula(value):
    """
    Formatea un número de cédula
    Ejemplo: 1234567 -> 1.234.567
    """
    if not value:
        return ''
    
    value = str(value).replace('.', '').replace('-', '').replace(' ', '')
    
    if len(value) <= 3:
        return value
    
    # Formatear con puntos cada 3 dígitos
    return '.'.join([value[max(i-3, 0):i] for i in range(len(value), 0, -3)][::-1])


@register.filter(name='format_telefono')
def format_telefono(value):
    """
    Formatea un número de teléfono
    Ejemplo: 0981234567 -> (0981) 234-567
    """
    if not value:
        return ''
    
    value = str(value).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    if len(value) == 10:
        return f"({value[:4]}) {value[4:7]}-{value[7:]}"
    
    return value


@register.filter(name='estado_badge')
def estado_badge(estado):
    """
    Retorna la clase CSS para el badge de estado
    """
    badges = {
        'activo': 'badge-success',
        'inactivo': 'badge-secondary',
        'suspendido': 'badge-warning',
        'retirado': 'badge-danger',
    }
    return badges.get(estado, 'badge-secondary')


@register.filter(name='salario_format')
def salario_format(value):
    """
    Formatea un salario con separador de miles
    Ejemplo: 250000 -> 250.000
    """
    if not value:
        return '0'
    
    try:
        return f"{int(float(value)):,}".replace(',', '.')
    except (ValueError, TypeError):
        return value


@register.simple_tag
def puede_editar_trabajador(user, trabajador):
    """
    Verifica si el usuario puede editar el trabajador
    """
    return user.es_administrador or trabajador.creado_por == user
