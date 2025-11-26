"""
Context processors para Core
apps/core/context_processors.py

Para que esté disponible en TODOS los templates
"""
from .utils import get_tipo_cambio_actual, get_configuracion_sistema


def configuracion_global(request):
    """
    Agrega la configuración global a todos los templates
    
    Uso en templates:
        {{ tipo_cambio_actual }}
        {{ nombre_empresa }}
    """
    config = get_configuracion_sistema()
    
    return {
        'tipo_cambio_actual': config.tipo_cambio_actual,
        'nombre_empresa': config.nombre_empresa,
        'configuracion_sistema': config,
    }