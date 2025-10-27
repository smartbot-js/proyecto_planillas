import os
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.usuarios.models import Usuario
from django.utils.text import slugify


def contrato_upload_path(instance, filename):
    """Ruta para contratos"""
    proyecto_slug = slugify(instance.nombre)
    return os.path.join('proyectos', proyecto_slug, 'contratos', filename)


def avaluo_upload_path(instance, filename):
    """Ruta para avalúos"""
    proyecto_slug = slugify(instance.nombre)
    return os.path.join('proyectos', proyecto_slug, 'avaluos', filename)


def presupuesto_upload_path(instance, filename):
    """Ruta para presupuestos"""
    proyecto_slug = slugify(instance.nombre)
    return os.path.join('proyectos', proyecto_slug, 'presupuestos', filename)


def imagen_upload_path(instance, filename):
    """Ruta para imágenes"""
    proyecto_slug = slugify(instance.nombre)
    return os.path.join('proyectos', proyecto_slug, 'imagenes', filename)


class Proyecto(models.Model):
    """Modelo para gestionar proyectos de construcción"""
    
    class Estado(models.TextChoices):
        PLANIFICACION = 'planificacion', 'En Planificación'
        EJECUCION = 'ejecucion', 'En Ejecución'
        PAUSADO = 'pausado', 'Pausado'
        FINALIZADO = 'finalizado', 'Finalizado'
        CANCELADO = 'cancelado', 'Cancelado'
    
    class TipoProyecto(models.TextChoices):
        RESIDENCIAL = 'residencial', 'Residencial'
        COMERCIAL = 'comercial', 'Comercial'
        PUBLICO = 'publico', 'Público'
        INDUSTRIAL = 'industrial', 'Industrial'
        MIXTO = 'mixto', 'Mixto'
    
    # Información básica
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Proyecto')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PLANIFICACION,
        verbose_name='Estado del Proyecto'
    )
    tipo_proyecto = models.CharField(
        max_length=20,
        choices=TipoProyecto.choices,
        default=TipoProyecto.RESIDENCIAL,
        verbose_name='Tipo de Proyecto'
    )
    
    # Ubicación
    ubicacion = models.CharField(max_length=300, verbose_name='Dirección')
    ubicacion_coordenadas = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Coordenadas GPS'
    )
    departamento = models.CharField(max_length=100, blank=True, verbose_name='Departamento')
    municipio = models.CharField(max_length=100, blank=True, verbose_name='Municipio')
    
    # Características del proyecto
    tamano_proyecto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Tamaño del Proyecto (m²)'
    )
    cantidad_unidades = models.IntegerField(default=0, verbose_name='Cantidad de Unidades')
    tamano_promedio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Tamaño Promedio (m²)'
    )
    
    # Fechas
    fecha_inicio = models.DateField(verbose_name='Fecha de Inicio')
    fecha_fin_estimada = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Finalización Estimada'
    )
    fecha_avaluo = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha del Avalúo'
    )
    
    # Gerencia y personal
    supervisor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='proyectos_supervisados',
        verbose_name='Supervisor/Gerente'
    )
    personal_asignado = models.IntegerField(default=0, verbose_name='Personal Asignado')
    contratistas_asignados = models.IntegerField(default=0, verbose_name='Contratistas Asignados')
    
    # Porcentajes
    porcentaje_avance_general = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de Avance General'
    )
    porcentaje_asignacion_planilla = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de Asignación de Planilla'
    )
    
    # Presupuesto
    presupuesto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Presupuesto Total'
    )
    presupuesto_mano_obra = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Presupuesto Mano de Obra'
    )
    presupuesto_administrativo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Presupuesto Administrativo'
    )
    
    # Gastos reales
    gasto_mano_obra_real = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Gasto Real Mano de Obra'
    )
    gasto_administrativo_real = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Gasto Real Administrativo'
    )
    
    # Anticipo y avalúo
    anticipo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Anticipo'
    )
    valor_avaluo_acumulado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor Avalúo Acumulado'
    )
    
    # Archivos
    archivo_contrato = models.FileField(
        upload_to=contrato_upload_path,
        blank=True,
        null=True,
        verbose_name='Archivo de Contrato'
    )
    archivo_avaluo = models.FileField(
        upload_to=avaluo_upload_path,
        blank=True,
        null=True,
        verbose_name='Archivo de Avalúo'
    )
    archivo_presupuesto = models.FileField(
        upload_to=presupuesto_upload_path,
        blank=True,
        null=True,
        verbose_name='Archivo de Presupuesto'
    )
    imagen_proyecto = models.ImageField(
        upload_to=imagen_upload_path,
        blank=True,
        null=True,
        verbose_name='Imagen del Proyecto'
    )
    
    # Metadatos
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    
    # 🆕 AUDITORÍA DE USUARIOS
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_creados',
        verbose_name='Creado por'
    )
    modificado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_modificados',
        verbose_name='Modificado por'
    )
    
    # 🆕 SOFT DELETE
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    fecha_eliminacion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Eliminación')
    eliminado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_eliminados',
        verbose_name='Eliminado por'
    )
    
    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['estado']),
            models.Index(fields=['supervisor']),
            models.Index(fields=['activo']),
            models.Index(fields=['eliminado']),
        ]
    
    def __str__(self):
        return self.nombre
    
    @property
    def porcentaje_gastado(self):
        """Calcula el porcentaje del presupuesto total gastado"""
        if self.presupuesto_total > 0:
            total_gastado = self.gasto_mano_obra_real + self.gasto_administrativo_real
            porcentaje = (total_gastado / self.presupuesto_total) * 100
            return min(porcentaje, 100)
        return 0
    
    @property
    def presupuesto_disponible(self):
        """Calcula el presupuesto disponible"""
        total_gastado = self.gasto_mano_obra_real + self.gasto_administrativo_real
        return self.presupuesto_total - total_gastado
    
    @property
    def slug(self):
        """Retorna el slug del proyecto para URLs"""
        return slugify(self.nombre)
    
    def puede_ser_editado_por(self, usuario):
        """Verifica si un usuario puede editar este proyecto"""
        return usuario.es_administrador() or self.supervisor == usuario
    
    def puede_ser_eliminado_por(self, usuario):
        """Verifica si un usuario puede eliminar este proyecto"""
        return usuario.es_administrador()
    
    def get_directorio_proyecto(self):
        """Retorna el path del directorio del proyecto"""
        return os.path.join('proyectos', self.slug)
    
    def soft_delete(self, usuario):
        """Marca el proyecto como eliminado (soft delete)"""
        from django.utils import timezone
        self.eliminado = True
        self.activo = False
        self.fecha_eliminacion = timezone.now()
        self.eliminado_por = usuario
        self.save()
    
    def restaurar(self):
        """Restaura un proyecto eliminado"""
        self.eliminado = False
        self.activo = True
        self.fecha_eliminacion = None
        self.eliminado_por = None
        self.save()
        