"""
Modelos para el módulo de Reportes
apps/reportes/models.py
"""
from django.db import models
from django.core.validators import FileExtensionValidator
from decimal import Decimal


class ConfiguracionEmpresa(models.Model):
    """
    Configuración global de la empresa para reportes
    Solo debe existir UN registro
    """
    nombre_empresa = models.CharField(
        max_length=200,
        default='QUADYCONS',
        verbose_name='Nombre de la Empresa'
    )
    
    logo_empresa = models.ImageField(
        upload_to='empresa/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg'])],
        verbose_name='Logo de la Empresa',
        help_text='Logo que aparecerá en todos los reportes (PNG, JPG o SVG)'
    )
    
    direccion = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Dirección'
    )
    
    telefono = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Teléfono'
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    
    ruc = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='RUC / RIF'
    )
    
    # Tipo de cambio por defecto
    tipo_cambio_default = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('36.60'),
        verbose_name='Tipo de Cambio por Defecto',
        help_text='Córdobas por cada Dólar (ej: 36.60)'
    )
    
    # Control de instancia única
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )
    
    class Meta:
        verbose_name = 'Configuración de Empresa'
        verbose_name_plural = 'Configuración de Empresa'
        db_table = 'configuracion_empresa'
    
    def __str__(self):
        return f"{self.nombre_empresa} - Configuración"
    
    def save(self, *args, **kwargs):
        """
        Asegurar que solo exista una configuración activa
        """
        if self.activo:
            # Desactivar todas las demás configuraciones
            ConfiguracionEmpresa.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_configuracion(cls):
        """
        Obtener la configuración activa o crear una por defecto
        """
        config, created = cls.objects.get_or_create(
            activo=True,
            defaults={
                'nombre_empresa': 'QUADYCONS',
                'tipo_cambio_default': Decimal('36.60')
            }
        )
        return config
        