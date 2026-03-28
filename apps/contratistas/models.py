"""
Modelos del módulo de Contratistas - COMPLETO Y LIMPIO
apps/contratistas/models.py

Sistema de gestión de contratistas con:
- Contratistas
- Contratos de Proyectos
- Avalúos (antes Pagos)
- Planillas de Contratistas
- Detalles de Planillas
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from django.db.models import Max
import re

class Contratista(models.Model):
    """
    Contratista externo que puede trabajar en múltiples proyectos
    """
    
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    
    TIPO_CUENTA_CHOICES = [
        ('ahorro', 'Ahorro'),
        ('corriente', 'Corriente'),
    ]
    
    MONEDA_CHOICES = [
        ('cordobas', 'Córdobas'),
        ('dolares', 'Dólares'),
    ]
    
    # Información personal
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellido = models.CharField(max_length=100, verbose_name='Apellido')
    numero_cedula = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número de Cédula',
        help_text='Formato: 001-DDMMYY-0000X'
    )
    foto_cedula = models.ImageField(
        upload_to='contratistas/cedulas/',
        null=True,
        blank=True,
        verbose_name='Foto de Cédula'
    )
    
    # Contacto
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Teléfono'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='Email'
    )
    direccion = models.TextField(verbose_name='Dirección')
    departamento = models.CharField(max_length=100, verbose_name='Departamento')
    municipio = models.CharField(max_length=100, verbose_name='Municipio')
    
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
    activo = models.BooleanField(default=True, verbose_name='Activo')
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
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
        related_name='contratos_contratistas',
        verbose_name='Proyecto'
    )
    
    # Información del contrato
    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name='Descripción del Contrato'
    )
    actividades = models.TextField(
        verbose_name='Actividades',
        help_text='Lista de actividades del contrato'
    )
    unidad_medida = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Unidad de Medida'
    )
    
    # Valor y fechas
    valor_contrato = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor del Contrato (C$)'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de Inicio')
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='en_proceso',
        verbose_name='Estado'
    )
    
    # Metadata
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
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
        verbose_name = 'Contrato de Proyecto'
        verbose_name_plural = 'Contratos de Proyectos'
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.codigo} - {self.contratista.nombre_completo} - {self.proyecto.nombre}"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        """Genera código único: CT-PRY001-001"""
        from django.db.models import Max
        import re
        
        proyecto_codigo = self.proyecto.codigo if hasattr(self.proyecto, 'codigo') else 'PRY'
        prefijo = f"CT-{proyecto_codigo}-"
        
        # Buscar el código más alto existente (incluye eliminados para evitar colisiones)
        ultimo_contrato = ContratoProyecto.objects.filter(
            codigo__startswith=prefijo
        ).aggregate(max_codigo=Max('codigo'))['max_codigo']
        
        if ultimo_contrato:
            # Extraer el número del código existente
            match = re.search(r'-(\d+)$', ultimo_contrato)
            if match:
                numero = int(match.group(1)) + 1
            else:
                numero = 1
        else:
            numero = 1
        
        return f"{prefijo}{numero:03d}"
    
    @property
    def total_pagado(self):
        """Retorna el total pagado en este contrato (suma de avalúos aprobados)"""
        total = self.avaluos.filter(
            eliminado=False,
            estado__in=['aprobado_contador', 'pagado']
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
    def cantidad_avaluos(self):
        """Retorna la cantidad de avalúos del contrato"""
        return self.avaluos.filter(eliminado=False).count()

    @property
    def avaluos_activos(self):
        """Retorna los avalúos no eliminados del contrato"""
        return self.avaluos.filter(eliminado=False).order_by('-fecha_pago')

class AvaluoContratista(models.Model):
    """
    Avalúo quincenal del contratista
    Antes llamado: PagoContratista
    
    Representa el avance periódico (quincenal) de un contrato
    El supervisor registra el % de avance y se calcula el monto correspondiente
    """
    
    FORMA_PAGO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque (CK)'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado_gerente', 'Aprobado por Gerente'),
        ('aprobado_contador', 'Aprobado por Contador'),
        ('pagado', 'Pagado'),
        ('rechazado', 'Rechazado'),
    ]
    
    # Código único del avalúo
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código',
        help_text='AV0825-001 (AV=Avalúo, 08=mes, 25=año, 001=número)'
    )
    
    # Relación con contrato
    contrato = models.ForeignKey(
        ContratoProyecto,
        on_delete=models.PROTECT,
        related_name='avaluos',
        verbose_name='Contrato'
    )
    
    # Campos para avalúos
    periodo_inicio = models.DateField(
        verbose_name='Inicio del Período',
        help_text='Fecha de inicio del período quincenal'
    )
    periodo_fin = models.DateField(
        verbose_name='Fin del Período',
        help_text='Fecha de fin del período quincenal'
    )
    porcentaje_avance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='% de Avance',
        help_text='Porcentaje acumulado de avance del contrato'
    )
    
    # Información del avalúo
    fecha_pago = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Registro'
    )
    concepto = models.CharField(
        max_length=500,
        verbose_name='Concepto/Descripción del Trabajo'
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
        help_text='C$/USD al momento del avalúo'
    )
    
    # Forma de pago
    forma_pago = models.CharField(
        max_length=20,
        choices=FORMA_PAGO_CHOICES,
        default='transferencia',
        verbose_name='Forma de Pago'
    )
    
    # Soporte del avalúo
    archivo_soporte = models.FileField(
        upload_to='contratistas/avaluos/',
        null=True,
        blank=True,
        verbose_name='Archivo Soporte del Avalúo'
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
        related_name='avaluos_ingresados',
        verbose_name='Ingresado Por (Supervisor)'
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
        related_name='avaluos_aprobados_gerente',
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
        related_name='avaluos_aprobados_contador',
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
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pagos_contratistas'
        verbose_name = 'Avalúo de Contratista'
        verbose_name_plural = 'Avalúos de Contratistas'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"{self.codigo} - {self.contrato.contratista.nombre_completo} - {self.porcentaje_avance}%"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        
        # Calcular monto en dólares
        if self.tipo_cambio and self.tipo_cambio > 0:
            self.monto_dolares = (self.monto_cordobas / self.tipo_cambio).quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        """Genera código único: AV0825-001"""

        fecha = datetime.now()
        mes = fecha.strftime('%m')
        anio = fecha.strftime('%y')
        prefijo = f"AV{mes}{anio}-"
        
        # Buscar el número más alto existente (incluye eliminados)
        ultimo = AvaluoContratista.objects.filter(
            codigo__startswith=prefijo
        ).aggregate(max_codigo=Max('codigo'))['max_codigo']
        
        if ultimo:
            match = re.search(r'-(\d+)$', ultimo)
            numero = int(match.group(1)) + 1 if match else 1
        else:
            numero = 1
        
        return f"{prefijo}{numero:03d}"
    
    def calcular_monto_desde_porcentaje(self):
        """Calcula el monto basado en el % de avance y valor del contrato"""
        if self.contrato and self.porcentaje_avance:
            # Monto acumulado según porcentaje
            monto_acumulado = (self.contrato.valor_contrato * self.porcentaje_avance) / 100
            # Restar lo ya pagado
            self.monto_cordobas = monto_acumulado - self.contrato.total_pagado
            return self.monto_cordobas
        return Decimal('0.00')
    
    def aprobar_gerente(self, usuario):
        """Aprueba el avalúo como gerente"""
        if self.estado != 'pendiente':
            raise ValueError("Solo se pueden aprobar avalúos en estado pendiente")
        
        self.estado = 'aprobado_gerente'
        self.aprobado_gerente_por = usuario
        self.fecha_aprobacion_gerente = timezone.now()
        self.save()
    
    def aprobar_contador(self, usuario):
        """Aprueba el avalúo como contador (aprobación final)"""
        if self.estado not in ['pendiente', 'aprobado_gerente']:
            raise ValueError("El avalúo no puede ser aprobado por el contador en su estado actual")
        
        self.estado = 'aprobado_contador'
        self.aprobado_contador_por = usuario
        self.fecha_aprobacion_contador = timezone.now()
        self.save()
    
    def marcar_pagado(self):
        """Marca el avalúo como pagado (cuando se procesa el pago real)"""
        if self.estado != 'aprobado_contador':
            raise ValueError("Solo se pueden marcar como pagados avalúos aprobados por el contador")
        
        self.estado = 'pagado'
        self.save()
    
    def rechazar(self, usuario, motivo):
        """Rechaza el avalúo"""
        self.estado = 'rechazado'
        self.motivo_rechazo = motivo
        self.save()


class PlanillaContratista(models.Model):
    """
    Planilla quincenal de pagos a contratistas
    Agrupa todos los avalúos aprobados de un período
    """
    
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('aprobada_gerente', 'Aprobada por Gerente'),
        ('aprobada_contador', 'Aprobada por Contador'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada'),
    ]
    
    # Código único
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código',
        help_text='PN0825-01 (PN=Planilla, 08=mes, 25=año, 01=número)'
    )
    
    # Relación con proyecto
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.PROTECT,
        related_name='planillas_contratistas',
        verbose_name='Proyecto'
    )
    
    # Nombre descriptivo
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Planilla',
        help_text='Ej: Planilla Proyecto Villa Fontana - Agosto 2025'
    )
    
    # Período
    periodo_inicio = models.DateField(verbose_name='Inicio del Período')
    periodo_fin = models.DateField(verbose_name='Fin del Período')
    
    # Tipo de cambio
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name='Tipo de Cambio BCN',
        help_text='Tipo de cambio del BCN al momento de generar la planilla'
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
        verbose_name='Estado'
    )
    
    # Totales
    total_cordobas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total en Córdobas'
    )
    total_dolares = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total en Dólares'
    )
    
    # Control de generación
    generada_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='planillas_contratistas_generadas',
        verbose_name='Generada Por'
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Generación'
    )
    
    # Aprobaciones
    aprobada_gerente_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planillas_contratistas_aprobadas_gerente',
        verbose_name='Aprobada por Gerente'
    )
    fecha_aprobacion_gerente = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Gerente'
    )
    
    aprobada_contador_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planillas_contratistas_aprobadas_contador',
        verbose_name='Aprobada por Contador'
    )
    fecha_aprobacion_contador = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Contador'
    )
    
    # Observaciones
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Metadata
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'planillas_contratistas'
        verbose_name = 'Planilla de Contratistas'
        verbose_name_plural = 'Planillas de Contratistas'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"{self.codigo} - {self.proyecto.nombre} - {self.periodo_inicio} a {self.periodo_fin}"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        
        # Generar nombre si no existe
        if not self.nombre:
            self.nombre = self.generar_nombre()
        
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        """Genera código único: PN0825-01"""
        fecha = self.periodo_fin if self.periodo_fin else datetime.now()
        mes = fecha.strftime('%m')
        anio = fecha.strftime('%y')
        
        # Contar planillas del mes actual
        numero = PlanillaContratista.objects.filter(
            periodo_fin__year=fecha.year,
            periodo_fin__month=fecha.month
        ).count() + 1
        
        return f"PN{mes}{anio}-{numero:02d}"
    
    def generar_nombre(self):
        """Genera nombre descriptivo"""
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        mes_nombre = meses.get(self.periodo_fin.month, '')
        anio = self.periodo_fin.year
        return f"Planilla {self.proyecto.nombre} - {mes_nombre} {anio}"
    
    def calcular_totales(self):
        """Calcula los totales de la planilla"""
        detalles = self.detalles.all()
        self.total_cordobas = sum(d.monto_cordobas for d in detalles)
        self.total_dolares = sum(d.monto_dolares for d in detalles)
        self.save()
    
    def aprobar_gerente(self, usuario):
        """Aprueba la planilla como gerente"""
        if self.estado != 'borrador':
            raise ValueError("Solo se pueden aprobar planillas en estado borrador")
        
        self.estado = 'aprobada_gerente'
        self.aprobada_gerente_por = usuario
        self.fecha_aprobacion_gerente = timezone.now()
        self.save()
    
    def aprobar_contador(self, usuario):
        """Aprueba la planilla como contador"""
        if self.estado not in ['borrador', 'aprobada_gerente']:
            raise ValueError("La planilla no puede ser aprobada por el contador en su estado actual")
        
        self.estado = 'aprobada_contador'
        self.aprobada_contador_por = usuario
        self.fecha_aprobacion_contador = timezone.now()
        self.save()
    
    def marcar_pagada(self):
        """Marca la planilla como pagada"""
        if self.estado != 'aprobada_contador':
            raise ValueError("Solo se pueden marcar como pagadas planillas aprobadas por el contador")
        
        self.estado = 'pagada'
        
        # Marcar todos los avalúos como pagados
        for detalle in self.detalles.all():
            detalle.avaluo.marcar_pagado()
        
        self.save()


class DetallePlanillaContratista(models.Model):
    """
    Detalle de una planilla de contratistas
    Cada registro representa un avalúo incluido en la planilla
    """
    
    # Relaciones
    planilla = models.ForeignKey(
        PlanillaContratista,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Planilla'
    )
    avaluo = models.ForeignKey(
        AvaluoContratista,
        on_delete=models.PROTECT,
        related_name='detalles_planilla',
        verbose_name='Avalúo'
    )
    
    # Datos denormalizados
    contratista_nombre = models.CharField(max_length=200, verbose_name='Nombre del Contratista')
    contratista_cedula = models.CharField(max_length=20, verbose_name='Cédula')
    contratista_telefono = models.CharField(max_length=20, null=True, blank=True, verbose_name='Teléfono')
    
    actividad = models.TextField(verbose_name='Actividad/Descripción')
    
    monto_cordobas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto en Córdobas'
    )
    monto_dolares = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto en Dólares'
    )
    
    forma_pago = models.CharField(max_length=20, verbose_name='Forma de Pago')
    
    # Datos bancarios
    banco = models.CharField(max_length=100, null=True, blank=True, verbose_name='Banco')
    numero_cuenta = models.CharField(max_length=50, null=True, blank=True, verbose_name='Cuenta')
    moneda_cuenta = models.CharField(max_length=20, null=True, blank=True, verbose_name='Moneda')
    
    # Orden
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'detalles_planillas_contratistas'
        verbose_name = 'Detalle de Planilla de Contratistas'
        verbose_name_plural = 'Detalles de Planillas de Contratistas'
        ordering = ['orden', 'contratista_nombre']
    
    def __str__(self):
        return f"{self.planilla.codigo} - {self.contratista_nombre}"
    
    def save(self, *args, **kwargs):
        # Denormalizar datos del avalúo y contratista
        if self.avaluo:
            contratista = self.avaluo.contrato.contratista
            self.contratista_nombre = contratista.nombre_completo
            self.contratista_cedula = contratista.numero_cedula
            self.contratista_telefono = contratista.telefono
            self.actividad = self.avaluo.concepto
            self.monto_cordobas = self.avaluo.monto_cordobas
            self.monto_dolares = self.avaluo.monto_dolares
            self.forma_pago = self.avaluo.get_forma_pago_display()
            self.banco = contratista.banco
            self.numero_cuenta = contratista.numero_cuenta
            self.moneda_cuenta = contratista.moneda_cuenta
        
        super().save(*args, **kwargs)
