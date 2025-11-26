"""
Utilidades para el módulo Core
apps/core/utils.py
"""
from decimal import Decimal
from .models import ConfiguracionSistema


def get_tipo_cambio_actual():
    """
    Obtiene el tipo de cambio actual del sistema
    
    Returns:
        Decimal: Tipo de cambio C$/USD
    
    Example:
        >>> tc = get_tipo_cambio_actual()
        >>> print(tc)
        Decimal('36.6000')
    """
    return ConfiguracionSistema.get_tipo_cambio_actual()


def convertir_cordobas_a_dolares(monto_cordobas, tipo_cambio=None):
    """
    Convierte córdobas a dólares
    
    Args:
        monto_cordobas (Decimal): Monto en córdobas
        tipo_cambio (Decimal, optional): TC personalizado. Si no se envía, usa el actual.
    
    Returns:
        Decimal: Monto en dólares
    
    Example:
        >>> dolares = convertir_cordobas_a_dolares(Decimal('3660.00'))
        >>> print(dolares)
        Decimal('100.00')
    """
    if tipo_cambio is None:
        tipo_cambio = get_tipo_cambio_actual()
    
    if tipo_cambio <= 0:
        return Decimal('0.00')
    
    resultado = monto_cordobas / tipo_cambio
    return resultado.quantize(Decimal('0.01'))


def convertir_dolares_a_cordobas(monto_dolares, tipo_cambio=None):
    """
    Convierte dólares a córdobas
    
    Args:
        monto_dolares (Decimal): Monto en dólares
        tipo_cambio (Decimal, optional): TC personalizado. Si no se envía, usa el actual.
    
    Returns:
        Decimal: Monto en córdobas
    
    Example:
        >>> cordobas = convertir_dolares_a_cordobas(Decimal('100.00'))
        >>> print(cordobas)
        Decimal('3660.00')
    """
    if tipo_cambio is None:
        tipo_cambio = get_tipo_cambio_actual()
    
    resultado = monto_dolares * tipo_cambio
    return resultado.quantize(Decimal('0.01'))


def get_configuracion_sistema():
    """
    Obtiene la configuración completa del sistema
    
    Returns:
        ConfiguracionSistema: Objeto de configuración
    """
    return ConfiguracionSistema.get_configuracion()