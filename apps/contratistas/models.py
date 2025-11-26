"""
Modelos para el módulo de Contratistas
apps/contratistas/models.py
"""

from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime


class Contratista(models.Model):
    """Contratista que realiza trabajos para la empresa"""
    
    TIPO_CUENTA_CHOICES = [
        ('ahorro', 'Cuenta de Ahorro'),
        ('corriente', 'Cuenta Corriente'),
    ]
    
    MONEDA_CHOICES = [
        ('cordobas', 'Córdobas (C$)'),
        ('dolares', 'Dólares ($)'),
    ]
    
    # Datos personales
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    apellido = models.CharField(
        max_length=100,
        verbose_name='Apellido'
    )
    numero_cedula = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{13}[A-Z]$',
                message='La cédula debe tener 13 dígitos seguidos de una letra mayúscula'
            )
        ],
        verbose_name='Número de Cédula',
        help_text='Formato: 0011234567890A'
    )
    foto_cedula = models.ImageField(
        upload_to='contratistas/cedulas/',
        null=True,
        blank=True,
        verbose_name='Foto de Cédula'
    )
    
    # Contacto
    telefono = models.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                regex=r'^\d{8}$',
                message='El teléfono debe tener exactamente 8 dígitos'
            )
        ],
        verbose_name='Teléfono'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='Correo Electrónico'
    )
    
    # Ubicación
    direccion = models.CharField(
        max_length=500,
        verbose_name='Dirección'
    )
    departamento = models.CharField(
        max_length=100,
        verbose_name='Departamento'
    )
    municipio = models.CharField(
        max_length=100,
        verbose_name='Municipio'
    )
    
    # Datos bancarios
    banco = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Banco'
    )
    numero_cuenta = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Número de Cuenta'
    )
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=TIPO_CUENTA_CHOICES,
        null=True,
        blank=True,
        verbose_name='Tipo de Cuenta'
    )
    moneda_cuenta = models.CharField(
        max_length=20,
        choices=MONEDA_CHOICES,
        default='cordobas',
        verbose_name='Moneda de la Cuenta'
    )
    
    # Metadata
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    eliminado = models.BooleanField(
        default=False,
        verbose_name='Eliminado'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contratistas_creados',
        verbose_name='Creado Por'
    )
    
    class Meta:
        db_table = 'contratistas'
        verbose_name = 'Contratista'
        verbose_name_plural = 'Contratistas'
        ordering = ['apellido', 'nombre']
    
    def __str__(self):
        return f"{self.apellido}, {self.nombre}"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del contratista"""
        return f"{self.nombre} {self.apellido}"
    
    @property
    def total_contratos(self):
        """Retorna el total de contratos del contratista"""
        return self.contratos.filter(eliminado=False).count()
    
    @property
    def total_pagado(self):
        """Retorna el total pagado al contratista en todos sus contratos"""
        total = Decimal('0.00')
        for contrato in self.contratos.filter(eliminado=False):
            total += contrato.total_pagado
        return total


class ContratoProyecto(models.Model):
    """
    Contrato entre un contratista y un proyecto
    Un contratista puede tener varios contratos en un mismo proyecto
    """
    
    ESTADO_CHOICES = [
        ('planificacion', 'En Planificación'),
        ('en_proceso', 'En Proceso'),
        ('pausado', 'Pausado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    # Código único del contrato
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código',
        help_text='Se genera automáticamente'
    )
    
    # Relaciones
    contratista = models.ForeignKey(
        Contratista,
        on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name='Contratista'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name='Proyecto'
    )
    
    # Información del contrato
    descripcion = models.TextField(
        verbose_name='Descripción del Alcance'
    )
    actividades = models.CharField(
        max_length=200,
        verbose_name='Actividades',
        help_text='Lista de actividades separadas por coma'
    )
    
    # Valores
    valor_contrato = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Original del Contrato'
    )
    
    # Fechas
    fecha_inicio = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        verbose_name='Fecha de Fin'
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='planificacion',
        verbose_name='Estado del Contrato'
    )
    
    # Metadata
    eliminado = models.BooleanField(
        default=False,
        verbose_name='Eliminado'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contratos_creados',
        verbose_name='Creado Por'
    )
    
    class Meta:
        db_table = 'contratos_proyectos'
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.codigo} - {self.contratista.nombre_completo} - {self.proyecto.nombre}"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        """Genera código único para el contrato: CT-PROY-001"""
        proyecto_codigo = self.proyecto.codigo[:4].upper() if hasattr(self.proyecto, 'codigo') and self.proyecto.codigo else 'PROY'
        numero = ContratoProyecto.objects.filter(
            proyecto=self.proyecto
        ).count() + 1
        return f"CT-{proyecto_codigo}-{numero:03d}"
    
    @property
    def total_pagado(self):
        """Retorna el total pagado en este contrato"""
        total = self.pagos.filter(
            eliminado=False,
            estado='aprobado'
        ).aggregate(
            total=models.Sum('monto_cordobas')
        )['total'] or Decimal('0.00')
        return total
    
    @property
    def total_pendiente(self):
        """Retorna el monto pendiente por pagar"""
        return self.valor_contrato - self.total_pagado
    
    @property
    def porcentaje_avance(self):
        """Retorna el porcentaje de avance según pagos"""
        if self.valor_contrato > 0:
            return (self.total_pagado / self.valor_contrato) * 100
        return 0
    
    @property
    def cantidad_pagos(self):
        """Retorna la cantidad de pagos realizados"""
        return self.pagos.filter(eliminado=False, estado='aprobado').count()


class PagoContratista(models.Model):
    """Pago realizado a un contratista por un contrato"""
    
    FORMA_PAGO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque (CK)'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado_gerente', 'Aprobado por Gerente'),
        ('aprobado', 'Aprobado Final'),
        ('rechazado', 'Rechazado'),
    ]
    
    # Código único del pago
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código',
        help_text='PN0725-01 (PN=Pago, 07=mes, 25=año, 01=número)'
    )
    
    # Relación con contrato
    contrato = models.ForeignKey(
        ContratoProyecto,
        on_delete=models.PROTECT,
        related_name='pagos',
        verbose_name='Contrato'
    )
    
    # Información del pago
    fecha_pago = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Pago'
    )
    concepto = models.CharField(
        max_length=500,
        verbose_name='Concepto/Descripción'
    )
    
    # Montos
    monto_cordobas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto en Córdobas'
    )
    monto_dolares = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Monto en Dólares'
    )
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('36.6000'),
        verbose_name='Tipo de Cambio',
        help_text='C$/USD al momento del pago'
    )
    
    # Forma de pago
    forma_pago = models.CharField(
        max_length=20,
        choices=FORMA_PAGO_CHOICES,
        default='transferencia',
        verbose_name='Forma de Pago'
    )
    
    # Soporte del pago
    archivo_soporte = models.FileField(
        upload_to='contratistas/soportes/',
        null=True,
        blank=True,
        verbose_name='Archivo Soporte'
    )
    
    # Estado y aprobaciones
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    
    # Control de aprobaciones
    ingresado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pagos_ingresados',
        verbose_name='Ingresado Por'
    )
    fecha_ingreso = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Ingreso'
    )
    
    aprobado_gerente_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_contratista_aprobados_gerente',
        verbose_name='Aprobado por Gerente'
    )
    fecha_aprobacion_gerente = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Gerente'
    )
    
    aprobado_contador_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos_contratista_aprobados_contador',
        verbose_name='Aprobado por Contador'
    )
    fecha_aprobacion_contador = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Contador'
    )
    
    motivo_rechazo = models.TextField(
        null=True,
        blank=True,
        verbose_name='Motivo de Rechazo'
    )
    
    # Observaciones
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Metadata
    eliminado = models.BooleanField(
        default=False,
        verbose_name='Eliminado'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pagos_contratistas'
        verbose_name = 'Pago a Contratista'
        verbose_name_plural = 'Pagos a Contratistas'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"{self.codigo} - {self.contrato.contratista.nombre_completo} - C$ {self.monto_cordobas}"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        
        # Calcular monto en dólares si no está definido
        if self.tipo_cambio and self.tipo_cambio > 0:
            self.monto_dolares = (self.monto_cordobas / self.tipo_cambio).quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        """Genera código único: PN0725-01"""
        fecha = datetime.now()
        mes = fecha.strftime('%m')
        anio = fecha.strftime('%y')
        
        # Contar pagos del mes actual
        numero = PagoContratista.objects.filter(
            fecha_pago__year=fecha.year,
            fecha_pago__month=fecha.month
        ).count() + 1
        
        return f"PN{mes}{anio}-{numero:02d}"
    
    def aprobar_gerente(self, usuario):
        """Aprueba el pago como gerente"""
        if self.estado != 'pendiente':
            raise ValueError("Solo se pueden aprobar pagos en estado pendiente")
        
        self.estado = 'aprobado_gerente'
        self.aprobado_gerente_por = usuario
        self.fecha_aprobacion_gerente = timezone.now()
        self.save()
    
    def aprobar_contador(self, usuario):
        """Aprueba el pago como contador (aprobación final)"""
        # Si no hay gerente, puede aprobar directo desde pendiente
        if self.estado not in ['pendiente', 'aprobado_gerente']:
            raise ValueError("El pago no puede ser aprobado por el contador en su estado actual")
        
        self.estado = 'aprobado'
        self.aprobado_contador_por = usuario
        self.fecha_aprobacion_contador = timezone.now()
        self.save()
    
    def rechazar(self, usuario, motivo):
        """Rechaza el pago"""
        self.estado = 'rechazado'
        self.motivo_rechazo = motivo
        self.save()
        