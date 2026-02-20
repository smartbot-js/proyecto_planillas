"""
Utilidades para el módulo de trabajadores
- Generación de códigos QR automáticos
- Parser de código de barras de cédula paraguaya
- Validación de identificación dual
"""

import qrcode
import json
import re
from io import BytesIO
from django.core.files import File
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

# ============================================
# NORMALIZACIÓN DE CÉDULA PARA BÚSQUEDA
# ============================================

def normalizar_cedula(cedula):
    """Quita guiones y espacios para comparación"""
    return cedula.replace('-', '').replace(' ', '').strip().upper()


def buscar_trabajador_por_cedula(cedula):
    """
    Busca un trabajador por cédula, sin importar si viene
    con guiones (287-221289-0000J) o sin ellos (2872212890000J).
    
    Args:
        cedula (str): Número de cédula en cualquier formato
    
    Returns:
        Trabajador o None
    """
    from .models import Trabajador
    from django.db.models.functions import Replace
    from django.db.models import Value
    
    cedula_limpia = normalizar_cedula(cedula)
    
    # Primero intenta búsqueda exacta (más rápido)
    try:
        return Trabajador.objects.get(numero_cedula=cedula, eliminado=False)
    except Trabajador.DoesNotExist:
        pass
    
    # Si no encuentra, busca normalizando los guiones de la BD
    try:
        return Trabajador.objects.annotate(
            cedula_limpia=Replace(
                Replace('numero_cedula', Value('-'), Value('')),
                Value(' '), Value('')
            )
        ).get(cedula_limpia=cedula_limpia, eliminado=False)
    except Trabajador.DoesNotExist:
        return None

# ============================================
# PARSER DE CÓDIGO DE BARRAS - CÉDULA PARAGUAYA
# ============================================

def parsear_cedula_paraguaya(codigo_barras_raw):
    """
    Parsea el código de barras de la cédula paraguaya y extrae datos relevantes
    
    Formato identificado:
    [10 dígitos cédula][relleno][apellidos][nombres][sexo][fecha_nacimiento][otros]
    
    Args:
        codigo_barras_raw (str): String completo del código de barras escaneado
    
    Returns:
        dict: Datos extraídos y parseados
    """
    
    try:
        # Limpiar el string de caracteres especiales
        codigo_limpio = codigo_barras_raw.replace('�', '|')
        
        # Extraer número de cédula (primeros 10 dígitos numéricos)
        match_cedula = re.search(r'^\d{10}', codigo_barras_raw)
        numero_cedula = match_cedula.group(0) if match_cedula else None
        
        if not numero_cedula:
            return {
                'exito': False,
                'error': 'No se pudo extraer el número de cédula',
                'datos': None
            }
        
        # Buscar apellidos y nombres (después de varios separadores)
        # Patrón: buscar palabras en mayúsculas después del número de cédula
        palabras = re.findall(r'[A-ZÁÉÍÓÚÑ]{2,}', codigo_barras_raw[10:])
        
        apellido_paterno = palabras[0] if len(palabras) > 0 else ''
        apellido_materno = palabras[1] if len(palabras) > 1 else ''
        primer_nombre = palabras[2] if len(palabras) > 2 else ''
        segundo_nombre = palabras[3] if len(palabras) > 3 else ''
        
        # Extraer sexo (M o F)
        match_sexo = re.search(r'[MF](?=\d{8})', codigo_barras_raw)
        sexo = match_sexo.group(0) if match_sexo else None
        
        # Extraer fecha de nacimiento (8 dígitos después del sexo: YYYYMMDD)
        if match_sexo:
            pos_sexo = match_sexo.start()
            fecha_str = codigo_barras_raw[pos_sexo+1:pos_sexo+9]
            
            if len(fecha_str) == 8 and fecha_str.isdigit():
                try:
                    anio = int(fecha_str[0:4])
                    mes = int(fecha_str[4:6])
                    dia = int(fecha_str[6:8])
                    fecha_nacimiento = f"{anio}-{mes:02d}-{dia:02d}"
                except:
                    fecha_nacimiento = None
            else:
                fecha_nacimiento = None
        else:
            fecha_nacimiento = None
        
        # Construir objeto de respuesta
        return {
            'exito': True,
            'error': None,
            'datos': {
                'numero_cedula': numero_cedula,
                'apellido_paterno': apellido_paterno,
                'apellido_materno': apellido_materno,
                'primer_nombre': primer_nombre,
                'segundo_nombre': segundo_nombre,
                'nombre_completo': f"{primer_nombre} {segundo_nombre} {apellido_paterno} {apellido_materno}".strip(),
                'sexo': 'masculino' if sexo == 'M' else 'femenino' if sexo == 'F' else None,
                'fecha_nacimiento': fecha_nacimiento,
                'codigo_barras_raw': codigo_barras_raw[:100] + '...'  # Primeros 100 chars para log
            }
        }
    
    except Exception as e:
        return {
            'exito': False,
            'error': f'Error al parsear código de barras: {str(e)}',
            'datos': None
        }


def validar_cedula_fisica(codigo_barras_raw):
    """
    Valida un código de barras de cédula física y busca al trabajador en BD
    
    Args:
        codigo_barras_raw (str): String del código de barras escaneado
    
    Returns:
        dict: Resultado de la validación con info del trabajador
    """
    from .models import Trabajador
    
    # Parsear código de barras
    resultado_parser = parsear_cedula_paraguaya(codigo_barras_raw)
    
    if not resultado_parser['exito']:
        return {
            'valido': False,
            'trabajador': None,
            'error': resultado_parser['error'],
            'datos_extraidos': None
        }
    
    datos = resultado_parser['datos']
    numero_cedula = datos['numero_cedula']
    
    # Buscar trabajador en BD (normalizado, acepta con/sin guiones)
    try:
        trabajador = buscar_trabajador_por_cedula(numero_cedula)
        
        if trabajador:
            coincidencias = {
                'cedula': True,
                'nombre': validar_similitud_nombre(
                    trabajador.nombre_completo, 
                    datos['nombre_completo']
                ),
            }
            
            return {
                'valido': True,
                'trabajador': trabajador,
                'error': None,
                'datos_extraidos': datos,
                'coincidencias': coincidencias
            }
        else:
            return {
                'valido': False,
                'trabajador': None,
                'error': f'No se encontró trabajador con cédula {numero_cedula}',
                'datos_extraidos': datos
            }
    
    except Exception as e:
        return {
            'valido': False,
            'trabajador': None,
            'error': f'Error al validar: {str(e)}',
            'datos_extraidos': datos
        }


def validar_similitud_nombre(nombre_bd, nombre_cedula):
    """
    Valida que los nombres sean similares (no necesariamente idénticos)
    
    Args:
        nombre_bd (str): Nombre en base de datos
        nombre_cedula (str): Nombre extraído de cédula
    
    Returns:
        bool: True si son similares
    """
    # Normalizar ambos nombres
    nombre_bd_norm = nombre_bd.upper().strip()
    nombre_cedula_norm = nombre_cedula.upper().strip()
    
    # Si son idénticos
    if nombre_bd_norm == nombre_cedula_norm:
        return True
    
    # Verificar si al menos uno contiene al otro
    if nombre_bd_norm in nombre_cedula_norm or nombre_cedula_norm in nombre_bd_norm:
        return True
    
    # Verificar coincidencia de apellidos
    palabras_bd = set(nombre_bd_norm.split())
    palabras_cedula = set(nombre_cedula_norm.split())
    
    coincidencias = palabras_bd.intersection(palabras_cedula)
    
    # Si al menos 2 palabras coinciden, consideramos válido
    return len(coincidencias) >= 2


# ============================================
# GENERACIÓN DE CÓDIGO QR
# ============================================

def generar_qr_trabajador(trabajador):
    """
    Genera un código QR para el trabajador con su número de cédula
    El QR será escaneado por la app móvil para registrar asistencias
    
    Args:
        trabajador: Instancia del modelo Trabajador
    
    Returns:
        str: Path relativo del archivo QR guardado
    """
    
    # Crear instancia de QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta corrección de errores
        box_size=10,
        border=4,
    )

    # Datos del QR en formato JSON
    datos_qr = {
        "cedula": trabajador.numero_cedula,
        "nombre": trabajador.nombre_completo,
        "cargo": trabajador.puesto_laboral or trabajador.area_cargo or "Sin asignar",
        "proyecto": trabajador.proyecto_asignado.nombre if trabajador.proyecto_asignado else None,
        "id_proyecto": trabajador.proyecto_asignado.id if trabajador.proyecto_asignado else None
    }

    # Datos del QR - Solo la cédula (identificador único)
#    qr.add_data(trabajador.numero_cedula)

    qr.add_data(json.dumps(datos_qr, ensure_ascii=False))

    qr.make(fit=True)
    
    # Crear imagen del QR
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a RGB si es necesario
    if img_qr.mode != 'RGB':
        img_qr = img_qr.convert('RGB')
    
    # Crear imagen con información adicional (más visual y profesional)
    img_final = crear_qr_con_info(img_qr, trabajador)
    
    # Guardar en memoria
    buffer = BytesIO()
    img_final.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    # Nombre del archivo
    filename = f'qr_{trabajador.numero_cedula}.png'
    
    # Guardar en el modelo
    trabajador.codigo_qr.save(filename, File(buffer), save=False)
    
    return trabajador.codigo_qr.name


def crear_qr_con_info(img_qr, trabajador):
    """
    Crea una imagen completa con el QR y la información del trabajador
    Diseño profesional para imprimir o mostrar
    
    Args:
        img_qr: Imagen PIL del código QR
        trabajador: Instancia del modelo Trabajador
    
    Returns:
        Image: Imagen PIL con QR e información
    """
    
    # Tamaño del QR original
    qr_width, qr_height = img_qr.size
    
    # Crear imagen más grande para agregar información
    padding = 50
    info_height = 180
    new_width = qr_width + (padding * 2)
    new_height = qr_height + info_height + (padding * 2)
    
    # Crear imagen blanca
    img_final = Image.new('RGB', (new_width, new_height), 'white')
    
    # Pegar el QR en el centro superior
    qr_x = padding
    qr_y = padding + 20
    img_final.paste(img_qr, (qr_x, qr_y))
    
    # Dibujar
    draw = ImageDraw.Draw(img_final)
    
    # Intentar cargar fuentes, si no existen usar default
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_text = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
            font_text = ImageFont.truetype("DejaVuSans.ttf", 20)
            font_small = ImageFont.truetype("DejaVuSans.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Posición del texto
    text_y = qr_y + qr_height + 30
    
    # Nombre del trabajador (centrado)
    nombre_completo = trabajador.nombre_completo.upper()
    bbox = draw.textbbox((0, 0), nombre_completo, font=font_title)
    text_width = bbox[2] - bbox[0]
    text_x = (new_width - text_width) // 2
    draw.text((text_x, text_y), nombre_completo, fill='#1f2937', font=font_title)
    
    # Línea separadora
    text_y += 45
    line_margin = 60
    draw.line([(line_margin, text_y), (new_width - line_margin, text_y)], fill='#e5e7eb', width=2)
    
    # Cédula (centrado)
    text_y += 20
    cedula_text = f"CI: {trabajador.numero_cedula}"
    bbox = draw.textbbox((0, 0), cedula_text, font=font_text)
    text_width = bbox[2] - bbox[0]
    text_x = (new_width - text_width) // 2
    draw.text((text_x, text_y), cedula_text, fill='#374151', font=font_text)
    
    # Cargo (centrado)
    text_y += 35
    cargo_text = trabajador.puesto_laboral
    bbox = draw.textbbox((0, 0), cargo_text, font=font_small)
    text_width = bbox[2] - bbox[0]
    text_x = (new_width - text_width) // 2
    draw.text((text_x, text_y), cargo_text, fill='#6b7280', font=font_small)
    
    # Proyecto si existe (centrado)
    if trabajador.proyecto_asignado:
        text_y += 28
        proyecto_text = f"Proyecto: {trabajador.proyecto_asignado.nombre}"
        bbox = draw.textbbox((0, 0), proyecto_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_x = (new_width - text_width) // 2
        draw.text((text_x, text_y), proyecto_text, fill='#9ca3af', font=font_small)
    
    return img_final


# ============================================
# VALIDACIÓN UNIFICADA (QR o CÓDIGO DE BARRAS)
# ============================================

def validar_identificacion_trabajador(codigo_escaneado):
    """
    Función unificada que detecta automáticamente si es QR o código de barras
    y valida al trabajador correspondiente
    
    Args:
        codigo_escaneado (str): String del código escaneado (QR o código de barras)
    
    Returns:
        dict: Resultado de validación con info del trabajador
    """
    from .models import Trabajador
    
    # Detectar tipo de código
    # Si es solo números y tiene 10 dígitos → Probablemente es nuestro QR
    # Si tiene caracteres especiales y es largo → Código de barras de cédula
    
    if len(codigo_escaneado) == 10 and codigo_escaneado.isdigit():
        # Es nuestro QR (solo cédula)
        tipo_codigo = 'QR_GENERADO'
        
        trabajador = buscar_trabajador_por_cedula(codigo_escaneado)
        
        if trabajador:
            return {
                'valido': True,
                'trabajador': trabajador,
                'tipo_codigo': tipo_codigo,
                'error': None
            }
        else:
            return {
                'valido': False,
                'trabajador': None,
                'tipo_codigo': tipo_codigo,
                'error': f'No se encontró trabajador con cédula {codigo_escaneado}'
            }
    
    else:
        # Es código de barras de cédula física
        tipo_codigo = 'CEDULA_FISICA'
        resultado = validar_cedula_fisica(codigo_escaneado)
        resultado['tipo_codigo'] = tipo_codigo
        return resultado
    