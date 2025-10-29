import os
from django.db import models
from django.utils.text import slugify


def trabajador_foto_path(instance, filename):
    """Ruta para foto del trabajador"""
    # Usar ID y cédula para organizar
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/foto{extension}'


def trabajador_cedula_frontal_path(instance, filename):
    """Ruta para foto de cédula frontal"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/cedula_frontal{extension}'


def trabajador_cedula_posterior_path(instance, filename):
    """Ruta para foto de cédula posterior"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/cedula_posterior{extension}'


def trabajador_record_policia_path(instance, filename):
    """Ruta para record de policía"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/record_policia{extension}'


def trabajador_contrato_path(instance, filename):
    """Ruta para contrato"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/contrato{extension}'


class Trabajador(models.Model):
    """Modelo para gestionar trabajadores de construcción"""
    
    # ... (todos los campos anteriores) ...
    
    # ========================================
    # DOCUMENTOS - MEJORADO
    # ========================================
    foto = models.ImageField(
        upload_to=trabajador_foto_path,
        blank=True,
        null=True,
        verbose_name='Foto del Trabajador'
    )
    
    foto_cedula_frontal = models.ImageField(
        upload_to=trabajador_cedula_frontal_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Frontal)'
    )
    
    foto_cedula_posterior = models.ImageField(
        upload_to=trabajador_cedula_posterior_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Posterior)'
    )
    
    # Mantener compatibilidad con código anterior
    foto_cedula = models.ImageField(
        upload_to=trabajador_cedula_frontal_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Única)'
    )
    
    record_policia_doc = models.FileField(
        upload_to=trabajador_record_policia_path,
        blank=True,
        null=True,
        verbose_name='Record de Policía'
    )
    
    archivo_contrato = models.FileField(
        upload_to=trabajador_contrato_path,
        blank=True,
        null=True,
        verbose_name='Archivo de Contrato'
    )
    
    # ... (resto del modelo) ...