"""
Datos de Puestos Laborales y Áreas de Trabajo
apps/core/puestos_data.py
"""

# Diccionario con áreas de trabajo y sus puestos laborales
PUESTOS_DATA = {
    'Administración': ['Bodega', 'Colaboradora', 'Guarda de Seguridad', 'Ingeniero Residente', 'Maestro de Obra', 'test puesto'],
    'Oficiales': ['Albañil', 'Electricista', 'Fontanero', 'Pintor', 'Soldador'],
    'Ayudante': ['Ayudante', 'Media Cuchara', 'Portero'],
    'Contratista': ['Contratista'],
    'Administrativa-General': ['Auxiliar de Camión', 'Auxiliar de Compras', 'Auxiliar de Formulación', 'Conductor', 'Contador General', 'Fiscal General', 'Gerente de Compras y Suministros', 'Gerente de Formulación', 'Gerente de Presupuesto', 'Gerente de Proyecto', 'Mensajero', 'Supervisor Bodegas', 'Supervisor General'],
    'test area': ['puesto 1'],
}

# Lista de áreas de trabajo ordenadas
AREAS_TRABAJO = list(PUESTOS_DATA.keys())

AREA_TRABAJO_CHOICES = [('', 'Seleccione un área')] + [(a, a) for a in AREAS_TRABAJO]

TODOS_PUESTOS = []
for puestos in PUESTOS_DATA.values():
    TODOS_PUESTOS.extend(puestos)
TODOS_PUESTOS = sorted(set(TODOS_PUESTOS))

PUESTO_LABORAL_CHOICES = [('', 'Seleccione un puesto')] + [(p, p) for p in TODOS_PUESTOS]

def get_puestos(area_trabajo):
    puestos = PUESTOS_DATA.get(area_trabajo, [])
    return sorted(puestos)

def get_puesto_choices(area_trabajo):
    puestos = get_puestos(area_trabajo)
    return [('', 'Seleccione un puesto')] + [(p, p) for p in puestos]

def get_all_puesto_choices():
    return PUESTO_LABORAL_CHOICES

def get_area_por_puesto(puesto):
    for area, puestos in PUESTOS_DATA.items():
        if puesto in puestos:
            return area
    return None

def validar_area_puesto(area_trabajo, puesto_laboral):
    if not area_trabajo or not puesto_laboral:
        return True
    puestos = PUESTOS_DATA.get(area_trabajo, [])
    return puesto_laboral in puestos
