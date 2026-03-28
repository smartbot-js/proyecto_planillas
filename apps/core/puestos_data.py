"""
Datos de Puestos Laborales y Áreas de Trabajo
apps/core/puestos_data.py
"""

# Diccionario con áreas de trabajo y sus puestos laborales
PUESTOS_DATA = {
    'Administración': [
        'Seguridad',
        'Bodega',
        'Maestro de Obra',
        'Ingeniero Residente',
        'Colaboradora'
    ],
    'Oficiales': [
        'Albañil',
        'Fontanero',
        'Pintor',
        'Soldador',
        'Electricista'
    ],
    'Ayudante': [
        'Ayudante',
        'Portero',
    ],
    'Contratista': [
        'Contratista',
    ],
    'Administrativa-General': [
        'Contador General',
        'Supervisor General',
        'Gerente de Presupuesto',
        'Gerente de Proyecto',
        'Gerente de Compras y Suministros',
        'Gerente de Formulación',
        'Auxiliar de Formulación',
        'Supervisor Bodegas',
        'Fiscal General',
        'Conductor',
        'Auxiliar de Compras',
        'Auxiliar de Camión',
        'Mensajero',
    ],
}

# Lista de áreas de trabajo ordenadas
AREAS_TRABAJO = list(PUESTOS_DATA.keys())

# Choices para usar en modelos Django
AREA_TRABAJO_CHOICES = [('', 'Seleccione un área')] + [(a, a) for a in AREAS_TRABAJO]

# Lista de todos los puestos laborales (sin duplicados)
TODOS_PUESTOS = []
for puestos in PUESTOS_DATA.values():
    TODOS_PUESTOS.extend(puestos)
TODOS_PUESTOS = sorted(set(TODOS_PUESTOS))

PUESTO_LABORAL_CHOICES = [('', 'Seleccione un puesto')] + [(p, p) for p in TODOS_PUESTOS]


def get_puestos(area_trabajo):
    """
    Obtiene la lista de puestos de un área de trabajo
    
    Args:
        area_trabajo: Nombre del área de trabajo
    
    Returns:
        list: Lista de puestos ordenados alfabéticamente
    """
    puestos = PUESTOS_DATA.get(area_trabajo, [])
    return sorted(puestos)


def get_puesto_choices(area_trabajo):
    """
    Obtiene las choices de puestos para un área de trabajo
    
    Args:
        area_trabajo: Nombre del área de trabajo
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para choices
    """
    puestos = get_puestos(area_trabajo)
    return [('', 'Seleccione un puesto')] + [(p, p) for p in puestos]


def get_all_puesto_choices():
    """
    Obtiene todas las choices de puestos de todas las áreas
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para choices
    """
    return PUESTO_LABORAL_CHOICES


def get_area_por_puesto(puesto):
    """
    Obtiene el área de trabajo correspondiente a un puesto
    
    Args:
        puesto: Nombre del puesto laboral
    
    Returns:
        str: Nombre del área de trabajo o None si no se encuentra
    """
    for area, puestos in PUESTOS_DATA.items():
        if puesto in puestos:
            return area
    return None


def validar_area_puesto(area_trabajo, puesto_laboral):
    """
    Valida que el puesto pertenezca al área de trabajo
    
    Args:
        area_trabajo: Nombre del área de trabajo
        puesto_laboral: Nombre del puesto laboral
    
    Returns:
        bool: True si el puesto pertenece al área
    """
    if not area_trabajo or not puesto_laboral:
        return True  # Si alguno está vacío, no validar
    
    puestos = PUESTOS_DATA.get(area_trabajo, [])
    return puesto_laboral in puestos
    