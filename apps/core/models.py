"""
Modelos para configuración global del sistema
apps/core/models.py
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class ConfiguracionSistema(models.Model):
    """
    Configuración global del sistema
    Solo puede existir UN registro (Singleton)
    """
    
    # Tipo de Cambio
    tipo_cambio_actual = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('36.6000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name='Tipo de Cambio Actual (C$/USD)',
        help_text='Tipo de cambio oficial para conversión de córdobas a dólares'
    )
    
    # Metadata de actualización
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )
    
    # Configuraciones adicionales (para futuro)
    nombre_empresa = models.CharField(
        max_length=200,
        default='Quadycons',
        verbose_name='Nombre de la Empresa'
    )
    
    class Meta:
        db_table = 'configuracion_sistema'
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuración del Sistema'
    
    def __str__(self):
        return f"Configuración - TC: C$ {self.tipo_cambio_actual}"
    
    def save(self, *args, **kwargs):
        # Forzar que siempre sea el mismo registro (pk=1)
        self.pk = 1
        super().save(*args, **kwargs)
        
        # Crear entrada en el historial solo si cambió el TC
        if self.pk and self.tipo_cambio_actual:
            ultimo_historial = HistorialTipoCambio.objects.order_by('-fecha_cambio').first()
            
            if not ultimo_historial or ultimo_historial.tipo_cambio != self.tipo_cambio_actual:
                HistorialTipoCambio.objects.create(
                    tipo_cambio=self.tipo_cambio_actual
                )
    
    @classmethod
    def get_configuracion(cls):
        """Obtiene o crea la configuración única del sistema"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    @classmethod
    def get_tipo_cambio_actual(cls):
        """Obtiene el tipo de cambio actual"""
        config = cls.get_configuracion()
        return config.tipo_cambio_actual


class HistorialTipoCambio(models.Model):
    """
    Historial de cambios del tipo de cambio
    Para auditoría y trazabilidad
    """
    
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name='Tipo de Cambio'
    )
    
    fecha_cambio = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha del Cambio'
    )
    
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observaciones'
    )
    
    class Meta:
        db_table = 'historial_tipo_cambio'
        verbose_name = 'Historial de Tipo de Cambio'
        verbose_name_plural = 'Historial de Tipos de Cambio'
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"TC: C$ {self.tipo_cambio} - {self.fecha_cambio.strftime('%d/%m/%Y %H:%M')}"