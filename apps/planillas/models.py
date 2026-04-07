"""
Modelos para el módulo de Planillas
Incluye: TipoCambio, DiaFeriado, Planilla, DetallePlanilla, PlanillaReembolso
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta


class TipoCambio(models.Model):
    """Tipo de cambio Córdoba/Dólar para cálculos de planilla"""
    
    fecha = models.DateField(
        default=timezone.now,
        unique=True,
        verbose_name='Fecha'
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('36.6000'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor (C$/USD)',
        help_text='Tipo de cambio oficial BCN'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Tipo de cambio actualmente en uso'
    )
    modificado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Modificado Por'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )
    
    class Meta:
        db_table = 'tipos_cambio'
        verbose_name = 'Tipo de Cambio'
        verbose_name_plural = 'Tipos de Cambio'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"C$ {self.valor} - {self.fecha.strftime('%d/%m/%Y')}"
    
    @classmethod
    def get_actual(cls):
        """Obtiene el tipo de cambio activo"""
        tipo_cambio = cls.objects.filter(activo=True).first()
        if not tipo_cambio:
            tipo_cambio = cls.objects.create(valor=Decimal('36.6000'))
        return tipo_cambio
    
class DiaFeriado(models.Model):
    """Días feriados nacionales y específicos de proyecto"""
    
    TIPO_CHOICES = [
        ('nacional', 'Nacional'),
        ('proyecto', 'Específico de Proyecto'),
    ]
    
    fecha = models.DateField(
        verbose_name='Fecha',
        db_index=True
    )
    descripcion = models.CharField(
        max_length=200,
        verbose_name='Descripción'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='nacional',
        verbose_name='Tipo'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='dias_feriados',
        verbose_name='Proyecto',
        help_text='Solo si es feriado específico de proyecto'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Creado Por'
    )
    
    class Meta:
        db_table = 'dias_feriados'
        verbose_name = 'Día Feriado'
        verbose_name_plural = 'Días Feriados'
        ordering = ['fecha']
        unique_together = [['fecha', 'tipo', 'proyecto']]
    
    def __str__(self):
        tipo_str = f" ({self.proyecto.nombre})" if self.proyecto else ""
        return f"{self.descripcion} - {self.fecha.strftime('%d/%m/%Y')}{tipo_str}"
    
    @classmethod
    def es_feriado(cls, fecha, proyecto=None):
        """Verifica si una fecha es feriado"""
        query = cls.objects.filter(fecha=fecha, activo=True)
        if proyecto:
            query = query.filter(models.Q(tipo='nacional') | models.Q(proyecto=proyecto))
        else:
            query = query.filter(tipo='nacional')
        return query.exists()
    
    @classmethod
    def cargar_feriados_pais(cls, pais='NI', anio=None):
        """
        Carga feriados nacionales usando la librería holidays
        
        Args:
            pais (str): Código ISO del país (NI=Nicaragua, CR=Costa Rica, etc.)
            anio (int): Año específico. Si es None, carga año actual y siguiente
        
        Returns:
            int: Cantidad de feriados cargados
        """
        try:
            import holidays
        except ImportError:
            raise ImportError(
                "La librería 'holidays' no está instalada. "
                "Instálala con: pip install holidays"
            )
        
        from datetime import datetime
        
        # Si no se especifica año, cargar año actual y siguiente
        if anio is None:
            anios = [datetime.now().year, datetime.now().year + 1]
        else:
            anios = [anio]
        
        contador = 0
        
        for anio_actual in anios:
            try:
                # Obtener feriados del país
                feriados_pais = holidays.country_holidays(pais, years=anio_actual)
                
                for fecha, nombre in feriados_pais.items():
                    # Crear o actualizar el feriado
                    obj, created = cls.objects.update_or_create(
                        fecha=fecha,
                        tipo='nacional',
                        proyecto=None,
                        defaults={
                            'descripcion': nombre,
                            'activo': True
                        }
                    )
                    if created:
                        contador += 1
                        
            except Exception as e:
                print(f"Error cargando feriados de {pais} para {anio_actual}: {str(e)}")
                continue
        
        return contador
    
    @classmethod
    def sincronizar_feriados_automatico(cls):
        """
        Sincroniza automáticamente los feriados del año actual y siguiente
        Se puede llamar desde un comando de management o task periódica
        """
        from datetime import datetime
        
        anio_actual = datetime.now().year
        
        # Verificar si ya existen feriados para este año
        if cls.objects.filter(
            fecha__year=anio_actual,
            tipo='nacional'
        ).exists():
            # Ya existen, solo cargar el siguiente año si no existe
            anio_siguiente = anio_actual + 1
            if not cls.objects.filter(
                fecha__year=anio_siguiente,
                tipo='nacional'
            ).exists():
                return cls.cargar_feriados_pais(anio=anio_siguiente)
            return 0
        else:
            # No existen, cargar ambos años
            return cls.cargar_feriados_pais()
    
    @classmethod
    def obtener_feriados_rango(cls, fecha_inicio, fecha_fin, proyecto=None):
        """
        Obtiene todos los feriados en un rango de fechas
        
        Args:
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            proyecto: Si se especifica, incluye feriados del proyecto
            
        Returns:
            QuerySet de DiaFeriado
        """
        query = cls.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
            activo=True
        )
        
        if proyecto:
            query = query.filter(
                models.Q(tipo='nacional') | models.Q(proyecto=proyecto)
            )
        else:
            query = query.filter(tipo='nacional')
        
        return query.order_by('fecha')
    
    @classmethod
    def contar_feriados_en_periodo(cls, fecha_inicio, fecha_fin, proyecto=None):
        """Cuenta la cantidad de días feriados en un período"""
        return cls.obtener_feriados_rango(fecha_inicio, fecha_fin, proyecto).count()

class Planilla(models.Model):
    """Planilla de pago por proyecto y período"""
    
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('aprobada_gerente', 'Aprobada por Gerente'),
        ('aprobada_final', 'Aprobada Final'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    
    # Información básica
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código',
        help_text='Se genera automáticamente'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.PROTECT,
        related_name='planillas',
        verbose_name='Proyecto'
    )
    periodo_inicio = models.DateField(
        verbose_name='Período Inicio',
        help_text='Se sugiere iniciar en jueves'
    )
    periodo_fin = models.DateField(
        verbose_name='Período Fin',
        help_text='Se sugiere terminar en martes'
    )
    
    # Moneda
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('36.6000'),
        verbose_name='Tipo de Cambio',
        help_text='C$/USD al momento de generar'
    )
    
    # Estado y aprobaciones
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
        verbose_name='Estado'
    )
    
    # Control de aprobaciones
    generada_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='planillas_generadas',
        verbose_name='Generada Por'
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Generación'
    )
    
    aprobada_gerente_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planillas_aprobadas_gerente',
        verbose_name='Aprobada Gerente Por'
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
        related_name='planillas_aprobadas_contador',
        verbose_name='Aprobada Contador Por'
    )
    fecha_aprobacion_contador = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Contador'
    )
    
    aprobada_final_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planillas_aprobadas_final',
        verbose_name='Aprobada Final Por'
    )
    fecha_aprobacion_final = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Aprobación Final'
    )
    
    pagada_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planillas_pagadas',
        verbose_name='Pagada Por'
    )
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Pago'
    )
    
    # Totales (se calculan automáticamente)
    total_cordobas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Córdobas'
    )
    total_dolares = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Dólares'
    )
    total_inss_laboral = models.DecimalField(
    max_digits=12,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name='Total INSS Laboral'
    )
    total_inss_patronal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total INSS Patronal'
    )
    total_inatec = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total INATEC'
    )
    # Observaciones y notas
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Soft delete
    eliminado = models.BooleanField(
        default=False,
        verbose_name='Eliminado'
    )
    
    # Timestamps
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'planillas'
        verbose_name = 'Planilla'
        verbose_name_plural = 'Planillas'
        ordering = ['-fecha_generacion']
        unique_together = [['proyecto', 'periodo_inicio', 'periodo_fin']]
    
    def __str__(self):
        return f"{self.codigo} - {self.proyecto.nombre} ({self.periodo_inicio.strftime('%d/%m/%Y')} - {self.periodo_fin.strftime('%d/%m/%Y')})"
    
    def save(self, *args, **kwargs):
        # Generar código si es nuevo
        if not self.pk and not self.codigo:
            self.codigo = self.generar_codigo()
        
        # Obtener tipo de cambio actual si no está definido
        if not self.tipo_cambio or self.tipo_cambio == 0:
            tipo_cambio_actual = TipoCambio.get_actual()
            self.tipo_cambio = tipo_cambio_actual.valor
        
        super().save(*args, **kwargs)
        
        # Calcular totales después de guardar (si ya tiene pk)
        if self.pk:
            self.calcular_totales()
    
    def generar_codigo(self):
        """Genera código único para la planilla"""
        from datetime import datetime
        from django.db.models import Max
        import re
        
        fecha = datetime.now()
        proyecto_codigo = self.proyecto.codigo[:4].upper() if hasattr(self.proyecto, 'codigo') and self.proyecto.codigo else 'PROY'
        prefijo = f"PL-{proyecto_codigo}-{fecha.year}-"
        
        ultimo = Planilla.objects.filter(
            codigo__startswith=prefijo
        ).aggregate(max_codigo=Max('codigo'))['max_codigo']
        
        if ultimo:
            match = re.search(r'-(\d+)$', ultimo)
            numero = int(match.group(1)) + 1 if match else 1
        else:
            numero = 1
        
        return f"{prefijo}{numero:04d}"

    def calcular_totales(self):
        """Calcula los totales de la planilla sumando todos los detalles"""
        from decimal import Decimal
        
        detalles = self.detalles.all()
        
        # Sumar todos los ingresos
        self.total_cordobas = sum(d.ingreso_total for d in detalles) or Decimal('0.00')
        self.total_dolares = self.total_cordobas / self.tipo_cambio if self.tipo_cambio else Decimal('0.00')
        
        self.total_inss_laboral = sum(d.inss_laboral for d in detalles) or Decimal('0.00')
        self.total_inss_patronal = sum(d.inss_patronal for d in detalles) or Decimal('0.00')
        self.total_inatec = sum(d.inatec for d in detalles) or Decimal('0.00')
        
        # Usar update para evitar recursión infinita
        Planilla.objects.filter(pk=self.pk).update(
            total_cordobas=self.total_cordobas,
            total_dolares=self.total_dolares,
            total_inss_laboral=self.total_inss_laboral,
            total_inss_patronal=self.total_inss_patronal,
            total_inatec=self.total_inatec
        )
    
    @property
    def puede_editar(self):
        """Verifica si la planilla puede editarse"""
        return self.estado in ['borrador', 'aprobada_gerente']
    
    @property
    def puede_aprobar_gerente(self):
        """Verifica si puede ser aprobada por gerente"""
        return self.estado == 'borrador'
    
    @property
    def puede_aprobar_contador(self):
        """Verifica si puede ser aprobada por contador"""
        return self.estado == 'aprobada_gerente'
    
    @property
    def puede_pagar(self):
        """Verifica si puede marcarse como pagada"""
        return self.estado == 'aprobada_final'
    
    @property
    def dias_periodo(self):
        """Retorna la cantidad de días del período"""
        return (self.periodo_fin - self.periodo_inicio).days + 1
    
    @property
    def inicia_jueves(self):
        """Verifica si el período inicia en jueves"""
        return self.periodo_inicio.weekday() == 3  # 0=Lunes, 3=Jueves
    
    @property
    def termina_martes(self):
        """Verifica si el período termina en martes"""
        return self.periodo_fin.weekday() == 1  # 1=Martes
    
    def aprobar_gerente(self, usuario):
        """Aprueba la planilla como gerente"""
        if not self.puede_aprobar_gerente:
            raise ValueError("La planilla no puede ser aprobada por el gerente en su estado actual")
        
        self.estado = 'aprobada_gerente'
        self.aprobada_gerente_por = usuario
        self.fecha_aprobacion_gerente = timezone.now()
        self.save()
    
    def aprobar_contador(self, usuario):
        """Aprueba la planilla como contador (aprobación final)"""
        if not self.puede_aprobar_contador:
            raise ValueError("La planilla no puede ser aprobada por el contador en su estado actual")
        
        self.estado = 'aprobada_final'
        self.aprobada_contador_por = usuario
        self.fecha_aprobacion_contador = timezone.now()
        self.aprobada_final_por = usuario
        self.fecha_aprobacion_final = timezone.now()
        self.save()
    
    def marcar_pagada(self, usuario):
        """Marca la planilla como pagada"""
        if not self.puede_pagar:
            raise ValueError("La planilla no puede marcarse como pagada en su estado actual")
        
        self.estado = 'pagada'
        self.pagada_por = usuario
        self.fecha_pago = timezone.now()
        self.save()
    
    def cancelar(self, usuario, motivo):
        """Cancela la planilla"""
        if self.estado == 'pagada':
            raise ValueError("No se puede cancelar una planilla ya pagada")
        
        self.estado = 'cancelada'
        self.observaciones += f"\n[CANCELADA por {usuario.get_full_name()} el {timezone.now().strftime('%d/%m/%Y %H:%M')}]\nMotivo: {motivo}"
        self.save()

class DetallePlanilla(models.Model):
    """Detalle de planilla por trabajador"""
    
    AREA_CHOICES = [
        ('administrativo', 'Administrativo de Proyecto'),
        ('oficiales', 'Oficiales'),
        ('ayudantes', 'Ayudantes'),
        ('guardas', 'Guardas de Seguridad'),
        ('subcontratista', 'Sub-Contratista'),
    ]
    
    # Relaciones
    planilla = models.ForeignKey(
        Planilla,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Planilla'
    )
    trabajador = models.ForeignKey(
        'trabajadores.Trabajador',
        on_delete=models.PROTECT,
        related_name='detalles_planilla',
        verbose_name='Trabajador'
    )
    
    # Clasificación
    area = models.CharField(
        max_length=20,
        choices=AREA_CHOICES,
        default='oficiales',
        verbose_name='Área'
    )
    cargo = models.CharField(
        max_length=100,
        verbose_name='Cargo'
    )
    
    # Días y horas trabajadas
    dias_laborados = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Días Laborados',
        help_text='Días efectivamente trabajados (máx 12 en catorcena)'
    )
    horas_normales = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas Normales'
    )
    horas_extras = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas Extras'
    )
    horas_dominicales = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas Dominicales',
        help_text='Horas trabajadas en domingo'
    )
    dias_feriados = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Días Feriados Trabajados'
    )
    
    # Salarios base
    salario_dia_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Día Base'
    )
    valor_septimo_dia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor 7mo Día',
        help_text='Calculado: salario_dia_base / 6'
    )
    salario_diario_con_septimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Diario + 7mo',
        help_text='salario_dia_base + valor_septimo_dia'
    )
    valor_hora_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Hora Base',
        help_text='Calculado: salario_dia_base / 12'
    )
    
    # Salarios devengados
    salario_devengado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Devengado',
        help_text='dias_laborados × salario_diario_con_septimo'
    )
    salario_horas_extras = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Horas Extras',
        help_text='(valor_hora_base × 2) × horas_extras'
    )
    salario_horas_dominicales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Horas Dominicales',
        help_text='(valor_hora_base × 2) × horas_dominicales'
    )
    salario_dias_feriados = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Días Feriados',
        help_text='Digitado por residente, autorizado por gerente'
    )
    
    # === CAMPOS PLANILLA (fórmulas Excel) ===
    vacaciones = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Vacaciones')
    aguinaldo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Aguinaldo')
    antiguedad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Antigüedad')
    salario_prestacionado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Salario Prestacionado')
    horas_feriado = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), verbose_name='Horas en Día Feriado')
    ingreso_dia_feriado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Ingreso Día Feriado')
    otros_ingresos = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Otros Ingresos')
    
    # === CAMPOS PARA PLANILLA ADMINISTRATIVA ===
    vacaciones = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Vacaciones',
        help_text='(2.5/30) × Salario Base'
    )
    aguinaldo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Aguinaldo',
        help_text='(2.5/30) × Salario Base'
    )
    antiguedad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Antigüedad',
        help_text='(2.5/30) × Salario Base'
    )
    salario_prestacionado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Prestacionado',
        help_text='Salario Base + Vacaciones + Aguinaldo + Antigüedad'
    )
    horas_feriado = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas en Día Feriado',
        help_text='Horas trabajadas en días feriados'
    )
    ingreso_dia_feriado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Ingreso Día Feriado',
        help_text='(Días Feriados × Día Base) + (Horas Feriado × Tarifa HE)'
    )
    otros_ingresos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Otros Ingresos'
    )
    # Fin campos planillas administrativa
    # Bonos y otros ingresos
    combustible = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Combustible',
        help_text='Digitado por residente, autorizado por gerente'
    )
    bonos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Bonos',
        help_text='Digitado por residente, autorizado por gerente'
    )
    # --- AÑADIR ESTE CAMPO ---
    deducciones = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Deducciones',
        help_text='Deducciones varias (ej. adelantos)'
    )
    otros_gastos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Otros Gastos'
    )
    otros_gastos_descripcion = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Descripción Otros Gastos'
    )
    
    # Total
    ingreso_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Ingreso Total'
    )
    inss_laboral = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name='INSS Laboral (6.25%)',
    help_text='Se descuenta al trabajador'
    )
    inss_patronal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='INSS Patronal (19%)',
        help_text='Lo paga la empresa'
    )
    inatec = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='INATEC (2%)',
        help_text='Lo paga la empresa'
    )
    
    # Control de ediciones
    editado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Editado Por'
    )
    fecha_edicion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Edición'
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    class Meta:
        db_table = 'detalles_planilla'
        verbose_name = 'Detalle de Planilla'
        verbose_name_plural = 'Detalles de Planilla'
        ordering = ['area', 'trabajador__apellido', 'trabajador__nombre']
        unique_together = [['planilla', 'trabajador']]
    
    def __str__(self):
        return f"{self.trabajador.nombre_completo} - {self.planilla.codigo}"
    
    def save(self, *args, **kwargs):
        self.calcular_valores()
        super().save(*args, **kwargs)
        
        if self.planilla_id:
            self.planilla.calcular_totales()
    
    def calcular_valores(self):
        """
        Fórmulas del Excel Planilla_Quadycons:
        - Trabajadores normales (por_hora): F=Día Base (hora×8), fórmula completa
        - Guardas (por_turno): F=Valor Turno (directo), sin HE ni feriados
        """
        dias = Decimal(str(self.dias_laborados))
        db = self.salario_dia_base  # F: Día Base o Valor Turno
        
        # Detectar si es trabajador por turno (guarda)
        es_por_turno = hasattr(self.trabajador, 'tipo_pago') and self.trabajador.tipo_pago == 'por_turno'
        
        if es_por_turno:
            self._calcular_valores_turno(dias, db)
            return

        # G: 7mo Día = (día_base / 6) × días_laborados
        self.valor_septimo_dia = ((db / Decimal('6')) * dias).quantize(Decimal('0.01')) if db > 0 and dias > 0 else Decimal('0.00')

        # H: Salario Base = días × día_base
        salario_base = (dias * db).quantize(Decimal('0.01'))
        self.salario_devengado = salario_base

        # Campos de referencia (compatibilidad con templates)
        self.salario_diario_con_septimo = (db + (db / Decimal('6'))).quantize(Decimal('0.01')) if db > 0 else Decimal('0.00')
        self.valor_hora_base = (db / Decimal('8')).quantize(Decimal('0.01')) if db > 0 else Decimal('0.00')

        # I, J, K: Prestaciones = (2.5/30) × Salario Base
        factor = Decimal('2.5') / Decimal('30')
        self.vacaciones = (factor * salario_base).quantize(Decimal('0.01'))
        self.aguinaldo = (factor * salario_base).quantize(Decimal('0.01'))
        self.antiguedad = (factor * salario_base).quantize(Decimal('0.01'))

        # L: Salario Prestacionado = Base + Vac + Ag + Ant + 7mo Día
        self.salario_prestacionado = (salario_base + self.vacaciones + self.aguinaldo + self.antiguedad + self.valor_septimo_dia).quantize(Decimal('0.01'))
        # N: Tarifa HE = (día_base / 8) × 2
        tarifa_he = (db / Decimal('8')) * Decimal('2') if db > 0 else Decimal('0.00')

        # O: Salario HE = tarifa × horas
        self.salario_horas_extras = (tarifa_he * self.horas_extras).quantize(Decimal('0.01'))

        # Dominicales (se pagan como extras)
        self.salario_horas_dominicales = (tarifa_he * self.horas_dominicales).quantize(Decimal('0.01'))

        # R: Ingreso Feriado = (días_feriados × día_base) + (horas_feriado × tarifa_he)
        self.ingreso_dia_feriado = (
            (Decimal(str(self.dias_feriados)) * db) + (self.horas_feriado * tarifa_he)
        ).quantize(Decimal('0.01'))
        self.salario_dias_feriados = self.ingreso_dia_feriado

        # W: Total = Prestacionado + HE + Dominicales + Feriado + Bonos + Combustible + Otros - Deducciones
        self.ingreso_total = (
            self.salario_prestacionado +
            self.salario_horas_extras +
            self.salario_horas_dominicales +
            self.ingreso_dia_feriado +
            self.bonos +
            self.combustible +
            self.otros_ingresos -
            self.deducciones
        ).quantize(Decimal('0.01'))

        # Cargas sociales (deshabilitado - no se usa en este proyecto)
        self.inss_laboral = Decimal('0.00')
        self.inss_patronal = Decimal('0.00')
        self.inatec = Decimal('0.00')

    def _calcular_valores_turno(self, turnos, valor_turno):
        """
        Fórmulas para guardas (por turno):
        - Sal. Base = turnos × valor_turno
        - 7mo = (valor_turno / 6) × turnos
        - Prestaciones sobre Sal. Base
        - No hay horas extras, feriados, dominicales
        """
        # G: 7mo Día
        self.valor_septimo_dia = ((valor_turno / Decimal('6')) * turnos).quantize(Decimal('0.01')) if valor_turno > 0 and turnos > 0 else Decimal('0.00')
        
        # H: Salario Base = turnos × valor_turno
        salario_base = (turnos * valor_turno).quantize(Decimal('0.01'))
        self.salario_devengado = salario_base
        
        # Campos de referencia
        self.salario_diario_con_septimo = (valor_turno + (valor_turno / Decimal('6'))).quantize(Decimal('0.01')) if valor_turno > 0 else Decimal('0.00')
        self.valor_hora_base = Decimal('0.00')
        
        # Prestaciones = (2.5/30) × Salario Base
        factor = Decimal('2.5') / Decimal('30')
        self.vacaciones = (factor * salario_base).quantize(Decimal('0.01'))
        self.aguinaldo = (factor * salario_base).quantize(Decimal('0.01'))
        self.antiguedad = (factor * salario_base).quantize(Decimal('0.01'))
        
        # L: Prestacionado = Base + Vac + Ag + Ant + 7mo
        self.salario_prestacionado = (salario_base + self.vacaciones + self.aguinaldo + self.antiguedad + self.valor_septimo_dia).quantize(Decimal('0.01'))
        
        # No hay HE, dominicales, ni feriados para guardas
        self.salario_horas_extras = Decimal('0.00')
        self.salario_horas_dominicales = Decimal('0.00')
        self.ingreso_dia_feriado = Decimal('0.00')
        self.salario_dias_feriados = Decimal('0.00')
        self.horas_feriado = Decimal('0.00')
        
        # W: Total = Prestacionado + Bonos + Combustible + Otros - Deducciones
        self.ingreso_total = (
            self.salario_prestacionado +
            self.bonos +
            self.combustible +
            self.otros_ingresos -
            self.deducciones
        ).quantize(Decimal('0.01'))
        
        # Cargas sociales (deshabilitado)
        self.inss_laboral = Decimal('0.00')
        self.inss_patronal = Decimal('0.00')
        self.inatec = Decimal('0.00')

    @property
    def ingreso_total_dolares(self):
        """Retorna el ingreso total en dólares"""
        if self.planilla.tipo_cambio > 0:
            return (self.ingreso_total / self.planilla.tipo_cambio).quantize(Decimal('0.01'))
        return Decimal('0.00')

class PlanillaReembolso(models.Model):
    """Planilla de reembolsos y otros gastos"""
    
    planilla = models.ForeignKey(
        Planilla,
        on_delete=models.CASCADE,
        related_name='reembolsos',
        verbose_name='Planilla'
    )
    numero_item = models.IntegerField(
        verbose_name='N°'
    )
    concepto = models.CharField(
        max_length=500,
        verbose_name='Concepto',
        help_text='Ej: INSS, INATEC, Horas Extra, PLOTER, etc.'
    )
    monto_cordobas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Monto Córdobas'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    # Audit
    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='reembolsos_creados',
        verbose_name='Creado Por'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'planillas_reembolsos'
        verbose_name = 'Reembolso y Otros Gastos'
        verbose_name_plural = 'Reembolsos y Otros Gastos'
        ordering = ['numero_item']
    
    def __str__(self):
        return f"{self.numero_item}. {self.concepto}"
    
    @property
    def monto_dolares(self):
        """Retorna el monto en dólares"""
        if self.planilla.tipo_cambio > 0:
            return (self.monto_cordobas / self.planilla.tipo_cambio).quantize(Decimal('0.01'))
        return Decimal('0.00')