from django import template

register = template.Library()

@register.filter
def tiene_permiso(user, permiso):
    try:
        # Superuser siempre puede todo
        if user.is_superuser:
            return True
        modulo, accion = permiso.split('.')
        return user.tiene_permiso(modulo, accion)
    except:
        return False