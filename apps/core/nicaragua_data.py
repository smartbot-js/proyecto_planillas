"""
Datos de Departamentos y Municipios de Nicaragua
apps/core/nicaragua_data.py
"""

# Diccionario con departamentos y sus municipios
NICARAGUA_DATA = {
    'Boaco': [
        'Boaco',
        'Camoapa',
        'San José de los Remates',
        'San Lorenzo',
        'Santa Lucía',
        'Teustepe',
    ],
    'Carazo': [
        'Diriamba',
        'Dolores',
        'El Rosario',
        'Jinotepe',
        'La Conquista',
        'La Paz de Carazo',
        'San Marcos',
        'Santa Teresa',
    ],
    'Chinandega': [
        'Chinandega',
        'Chichigalpa',
        'Cinco Pinos',
        'Corinto',
        'El Realejo',
        'El Viejo',
        'Posoltega',
        'Puerto Morazán',
        'San Francisco del Norte',
        'San Pedro del Norte',
        'Santo Tomás del Norte',
        'Somotillo',
        'Villanueva',
    ],
    'Chontales': [
        'Acoyapa',
        'Comalapa',
        'Cuapa',
        'El Coral',
        'Juigalpa',
        'La Libertad',
        'San Francisco de Cuapa',
        'San Pedro de Lóvago',
        'Santo Domingo',
        'Santo Tomás',
        'Villa Sandino',
    ],
    'Costa Caribe Norte': [
        'Bilwi (Puerto Cabezas)',
        'Bonanza',
        'Mulukukú',
        'Prinzapolka',
        'Rosita',
        'Siuna',
        'Waslala',
        'Waspán',
    ],
    'Costa Caribe Sur': [
        'Bluefields',
        'Corn Island',
        'Desembocadura de Río Grande',
        'El Ayote',
        'El Rama',
        'El Tortuguero',
        'Kukra Hill',
        'La Cruz de Río Grande',
        'Laguna de Perlas',
        'Muelle de los Bueyes',
        'Nueva Guinea',
        'Paiwas',
    ],
    'Estelí': [
        'Condega',
        'Estelí',
        'La Trinidad',
        'Pueblo Nuevo',
        'San Juan de Limay',
        'San Nicolás',
    ],
    'Granada': [
        'Diriá',
        'Diriomo',
        'Granada',
        'Nandaime',
    ],
    'Jinotega': [
        'Bocay',
        'El Cuá',
        'Jinotega',
        'La Concordia',
        'San José de Bocay',
        'San Rafael del Norte',
        'San Sebastián de Yalí',
        'Santa María de Pantasma',
        'Wiwilí de Jinotega',
    ],
    'León': [
        'Achuapa',
        'El Jicaral',
        'El Sauce',
        'La Paz Centro',
        'Larreynaga',
        'León',
        'Nagarote',
        'Quezalguaque',
        'Santa Rosa del Peñón',
        'Telica',
    ],
    'Madriz': [
        'Las Sabanas',
        'Palacagüina',
        'San José de Cusmapa',
        'San Juan de Río Coco',
        'San Lucas',
        'Somoto',
        'Telpaneca',
        'Totogalpa',
        'Yalagüina',
    ],
    'Managua': [
        'Ciudad Sandino',
        'El Crucero',
        'Managua',
        'Mateare',
        'San Francisco Libre',
        'San Rafael del Sur',
        'Ticuantepe',
        'Tipitapa',
        'Villa El Carmen',
    ],
    'Masaya': [
        'Catarina',
        'La Concepción',
        'Masatepe',
        'Masaya',
        'Nandasmo',
        'Nindirí',
        'Niquinohomo',
        'San Juan de Oriente',
        'Tisma',
    ],
    'Matagalpa': [
        'Ciudad Darío',
        'El Tuma - La Dalia',
        'Esquipulas',
        'Matagalpa',
        'Matiguás',
        'Muy Muy',
        'Rancho Grande',
        'Río Blanco',
        'San Dionisio',
        'San Isidro',
        'San Ramón',
        'Sébaco',
        'Terrabona',
    ],
    'Nueva Segovia': [
        'Ciudad Antigua',
        'Dipilto',
        'El Jícaro',
        'Jalapa',
        'Macuelizo',
        'Mozonte',
        'Murra',
        'Ocotal',
        'Quilalí',
        'San Fernando',
        'Santa María',
        'Wiwilí de Nueva Segovia',
    ],
    'Río San Juan': [
        'El Almendro',
        'El Castillo',
        'Morrito',
        'San Carlos',
        'San Juan del Norte',
        'San Miguelito',
    ],
    'Rivas': [
        'Altagracia',
        'Belén',
        'Buenos Aires',
        'Cárdenas',
        'Moyogalpa',
        'Potosí',
        'Rivas',
        'San Jorge',
        'San Juan del Sur',
        'Tola',
    ],
}

# Lista de departamentos ordenados alfabéticamente
DEPARTAMENTOS = sorted(NICARAGUA_DATA.keys())

# Choices para usar en modelos Django
DEPARTAMENTO_CHOICES = [('', 'Seleccione un departamento')] + [(d, d) for d in DEPARTAMENTOS]

def get_municipios(departamento):
    """
    Obtiene la lista de municipios de un departamento
    
    Args:
        departamento: Nombre del departamento
    
    Returns:
        list: Lista de municipios ordenados alfabéticamente
    """
    municipios = NICARAGUA_DATA.get(departamento, [])
    return sorted(municipios)

def get_municipio_choices(departamento):
    """
    Obtiene las choices de municipios para un departamento
    
    Args:
        departamento: Nombre del departamento
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para choices
    """
    municipios = get_municipios(departamento)
    return [('', 'Seleccione un municipio')] + [(m, m) for m in municipios]

def get_all_municipio_choices():
    """
    Obtiene todas las choices de municipios de todos los departamentos
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para choices
    """
    all_municipios = set()
    for municipios in NICARAGUA_DATA.values():
        all_municipios.update(municipios)
    
    return [('', 'Seleccione un municipio')] + [(m, m) for m in sorted(all_municipios)]

def validar_departamento_municipio(departamento, municipio):
    """
    Valida que el municipio pertenezca al departamento
    
    Args:
        departamento: Nombre del departamento
        municipio: Nombre del municipio
    
    Returns:
        bool: True si el municipio pertenece al departamento
    """
    if not departamento or not municipio:
        return True  # Si alguno está vacío, no validar
    
    municipios = NICARAGUA_DATA.get(departamento, [])
    return municipio in municipios
    