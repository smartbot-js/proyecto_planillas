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

class ReporteGastos(models.Model):
    """Reporte de gastos varios y reembolsos - Global de la empresa"""
    
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('aprobada_gerente', 'Aprobada por Gerente'),
        ('aprobada_contador', 'Aprobada por Contador'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada'),
    ]
    
    codigo = models.CharField(
        max_length=20, unique=True,
        verbose_name='Código',
        help_text='Se genera automáticamente'
    )
    periodo_inicio = models.DateField(verbose_name='Período Inicio')
    periodo_fin = models.DateField(verbose_name='Período Fin')
    
    tipo_cambio = models.DecimalField(
        max_digits=10, decimal_places=4,
        default=Decimal('36.6000'),
        verbose_name='Tipo de Cambio (C$/USD)'
    )
    
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='borrador', verbose_name='Estado'
    )
    
    # Totales calculados
    total_cordobas = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'), verbose_name='Total Córdobas'
    )
    total_dolares = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'), verbose_name='Total Dólares'
    )
    
    # Aprobaciones
    generado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True,
        related_name='reportes_gastos_generados', verbose_name='Generado Por'
    )
    aprobada_gerente_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reportes_gastos_aprobados_gerente', verbose_name='Aprobada Gerente Por'
    )
    fecha_aprobacion_gerente = models.DateTimeField(null=True, blank=True)
    
    aprobada_contador_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reportes_gastos_aprobados_contador', verbose_name='Aprobada Contador Por'
    )
    fecha_aprobacion_contador = models.DateTimeField(null=True, blank=True)
    
    pagada_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reportes_gastos_pagados', verbose_name='Pagada Por'
    )
    fecha_pago = models.DateTimeField(null=True, blank=True)
    
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reportes_gastos'
        verbose_name = 'Reporte de Gastos'
        verbose_name_plural = 'Reportes de Gastos'
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"{self.codigo} ({self.periodo_inicio.strftime('%d/%m/%Y')} - {self.periodo_fin.strftime('%d/%m/%Y')})"
    
    def save(self, *args, **kwargs):
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        from datetime import datetime
        import re
        fecha = datetime.now()
        prefijo = f"RG{fecha.strftime('%m%y')}-"
        ultimo = ReporteGastos.objects.filter(
            codigo__startswith=prefijo
        ).order_by('-codigo').first()
        if ultimo:
            match = re.search(r'-(\d+)$', ultimo.codigo)
            numero = int(match.group(1)) + 1 if match else 1
        else:
            numero = 1
        return f"{prefijo}{numero:02d}"
    
    def calcular_totales(self):
        from django.db.models import Sum
        total_c = self.detalles.aggregate(total=Sum('monto_cordobas'))['total'] or Decimal('0.00')
        self.total_cordobas = total_c
        self.total_dolares = (total_c / self.tipo_cambio).quantize(Decimal('0.01')) if self.tipo_cambio > 0 else Decimal('0.00')
        ReporteGastos.objects.filter(pk=self.pk).update(
            total_cordobas=self.total_cordobas,
            total_dolares=self.total_dolares
        )
    
    @property
    def puede_editar(self):
        return self.estado in ['borrador', 'aprobada_gerente']
    
    @property
    def cantidad_detalles(self):
        return self.detalles.count()


class DetalleReporteGastos(models.Model):
    """Línea individual de gasto/reembolso"""
    
    reporte = models.ForeignKey(
        ReporteGastos, on_delete=models.CASCADE,
        related_name='detalles', verbose_name='Reporte'
    )
    numero_item = models.IntegerField(verbose_name='N°')
    concepto = models.CharField(
        max_length=500, verbose_name='Concepto',
        help_text='Ej: INSS, INATEC, Combustible, Transporte, etc.'
    )
    monto_cordobas = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'), verbose_name='Monto Córdobas'
    )
    monto_dolares = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'), verbose_name='Monto Dólares'
    )
    archivo_soporte = models.FileField(
        upload_to='reportes/gastos/soportes/',
        max_length=500, null=True, blank=True,
        verbose_name='Archivo Soporte',
        help_text='Factura o recibo de soporte'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    
    creado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True,
        verbose_name='Creado Por'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'detalles_reporte_gastos'
        verbose_name = 'Detalle de Gasto'
        verbose_name_plural = 'Detalles de Gastos'
        ordering = ['numero_item']
    
    def __str__(self):
        return f"{self.numero_item}. {self.concepto} - C$ {self.monto_cordobas}"
    
    def save(self, *args, **kwargs):
        # Calcular dólares automáticamente
        if self.reporte.tipo_cambio > 0:
            self.monto_dolares = (self.monto_cordobas / self.reporte.tipo_cambio).quantize(Decimal('0.01'))
        # Auto-numerar si es nuevo
        if not self.pk and not self.numero_item:
            ultimo = DetalleReporteGastos.objects.filter(reporte=self.reporte).order_by('-numero_item').first()
            self.numero_item = (ultimo.numero_item + 1) if ultimo else 1
        super().save(*args, **kwargs)
        # Recalcular totales del reporte
        self.reporte.calcular_totales()
        