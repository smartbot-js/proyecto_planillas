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

@register.filter
def dolares(value):
    """1192.78 → $ 1,192.78"""
    try:
        return '$ {:,.2f}'.format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def horas_legible(value):
    """
    Convierte horas decimales a formato legible:
    0.00 → 0min
    0.10 → 6min
    0.50 → 30min
    1.00 → 1h
    1.50 → 1h 30min
    8.00 → 8h
    9.60 → 9h 36min
    """
    try:
        total = float(value)
        if total <= 0:
            return '0min'
        
        horas = int(total)
        minutos = round((total - horas) * 60)
        
        # Ajustar si minutos llega a 60
        if minutos >= 60:
            horas += 1
            minutos = 0
        
        if horas == 0:
            return f'{minutos}min'
        elif minutos == 0:
            return f'{horas}h'
        else:
            return f'{horas}h {minutos}min'
    except (ValueError, TypeError):
        return value


@register.filter
def hora_12h(value):
    """
    Convierte time o string HH:MM a formato 12h:
    07:00 → 7:00 AM
    16:30 → 4:30 PM
    """
    try:
        if hasattr(value, 'strftime'):
            return value.strftime('%I:%M %p').lstrip('0')
        
        # Si es string "HH:MM"
        parts = str(value).split(':')
        hora = int(parts[0])
        minuto = parts[1] if len(parts) > 1 else '00'
        
        if hora == 0:
            return f'12:{minuto} AM'
        elif hora < 12:
            return f'{hora}:{minuto} AM'
        elif hora == 12:
            return f'12:{minuto} PM'
        else:
            return f'{hora - 12}:{minuto} PM'
    except (ValueError, TypeError, IndexError):
        return value
        