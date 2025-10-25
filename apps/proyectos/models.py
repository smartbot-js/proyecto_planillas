"""
Modelos de la aplicación de proyectos
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal


class Proyecto(models.Model):
    """
    Modelo de Proyecto (Obra/Construcción)
    
    Representa un proyecto de construcción que puede tener trabajadores
    asignados y un supervisor responsable.
    """
    
    class Estado(models.TextChoices):
        """Estados posibles de un proyecto"""
        ACTIVO = 'activo', _('Activo')
        PAUSADO = 'pausado', _('Pausado')
        FINALIZADO = 'finalizado', _('Finalizado')
        CANCELADO = 'cancelado', _('Cancelado')
    
    # Información básica
    nombre = models.CharField(
        _('Nombre del Proyecto'),
        max_length=200,
        help_text=_('Nombre identificador del proyecto u obra')
    )
    
    descripcion = models.TextField(
        _('Descripción'),
        blank=True,
        help_text=_('Descripción detallada del proyecto')
    )
    
    ubicacion = models.CharField(
        _('Ubicación'),
        max_length=300,
        help_text=_('Dirección o ubicación del proyecto')
    )
    
    # Fechas
    fecha_inicio = models.DateField(
        _('Fecha de Inicio'),
        help_text=_('Fecha de inicio del proyecto')
    )
    
    fecha_fin_estimada = models.DateField(
        _('Fecha Fin Estimada'),
        null=True,
        blank=True,
        help_text=_('Fecha estimada de finalización')
    )
    
    fecha_fin_real = models.DateField(
        _('Fecha Fin Real'),
        null=True,
        blank=True,
        help_text=_('Fecha real de finalización del proyecto')
    )
    
    # Relaciones
    supervisor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='proyectos_supervisados',
        limit_choices_to={'rol__in': ['administrador', 'supervisor']},
        verbose_name=_('Supervisor'),
        help_text=_('Supervisor responsable del proyecto')
    )
    
    # Estado y presupuesto
    estado = models.CharField(
        _('Estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        help_text=_('Estado actual del proyecto')
    )
    
    presupuesto = models.DecimalField(
        _('Presupuesto Total'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Presupuesto total asignado al proyecto')
    )
    
    presupuesto_gastado = models.DecimalField(
        _('Presupuesto Gastado'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Monto del presupuesto ya utilizado')
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(
        _('Fecha de Creación'),
        auto_now_add=True
    )
    
    fecha_actualizacion = models.DateTimeField(
        _('Fecha de Actualización'),
        auto_now=True
    )
    
    class Meta:
        verbose_name = _('Proyecto')
        verbose_name_plural = _('Proyectos')
        ordering = ['-fecha_creacion']
        db_table = 'proyectos'
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['supervisor']),
            models.Index(fields=['fecha_inicio']),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"
    
    def es_activo(self):
        """Verifica si el proyecto está activo"""
        return self.estado == self.Estado.ACTIVO
    
    def es_finalizado(self):
        """Verifica si el proyecto está finalizado"""
        return self.estado == self.Estado.FINALIZADO
    
    def presupuesto_disponible(self):
        """Calcula el presupuesto disponible"""
        return self.presupuesto - self.presupuesto_gastado
    
    def porcentaje_gastado(self):
        """Calcula el porcentaje del presupuesto gastado"""
        if self.presupuesto > 0:
            return (self.presupuesto_gastado / self.presupuesto) * 100
        return 0
    
    def dias_transcurridos(self):
        """Calcula los días transcurridos desde el inicio"""
        from django.utils import timezone
        if self.fecha_fin_real:
            dias = (self.fecha_fin_real - self.fecha_inicio).days
        else:
            dias = (timezone.now().date() - self.fecha_inicio).days
        return max(0, dias)
    
    def dias_restantes(self):
        """Calcula los días restantes hasta la fecha estimada"""
        from django.utils import timezone
        if self.fecha_fin_estimada and not self.fecha_fin_real:
            dias = (self.fecha_fin_estimada - timezone.now().date()).days
            return max(0, dias)
        return 0
    
    def puede_ser_editado_por(self, usuario):
        """Verifica si un usuario puede editar el proyecto"""
        return usuario.es_administrador() or usuario.id == self.supervisor.id
    
    def activar(self):
        """Activa el proyecto"""
        self.estado = self.Estado.ACTIVO
        self.save()
    
    def pausar(self):
        """Pausa el proyecto"""
        self.estado = self.Estado.PAUSADO
        self.save()
    
    def finalizar(self):
        """Finaliza el proyecto"""
        from django.utils import timezone
        self.estado = self.Estado.FINALIZADO
        if not self.fecha_fin_real:
            self.fecha_fin_real = timezone.now().date()
        self.save()
    
    def cancelar(self):
        """Cancela el proyecto"""
        self.estado = self.Estado.CANCELADO
        self.save()

