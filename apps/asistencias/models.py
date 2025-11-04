from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import datetime, timedelta, time
from decimal import Decimal


class Asistencia(models.Model):
    """Modelo para el registro de asistencias de trabajadores"""
    
    # Choices como atributos de clase
    ESTADO_CHOICES = [
        ('abierto', 'Turno Abierto'),
        ('cerrado', 'Turno Cerrado'),
        ('editado', 'Editado Manualmente'),
        ('sincronizado', 'Sincronizado con App'),
    ]
    
    METODO_CHOICES = [
        ('qr', 'Código QR'),
        ('cedula', 'Cédula Física'),
        ('manual', 'Registro Manual'),
    ]
    
    # Relaciones
    trabajador = models.ForeignKey(
        'trabajadores.Trabajador',
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Trabajador'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Proyecto'
    )
    
    # Datos básicos
    fecha = models.DateField(default=timezone.now, verbose_name='Fecha')
    puesto_laboral = models.CharField(max_length=100, verbose_name='Puesto Laboral')

    # Salarios (copiados del trabajador al momento de la asistencia)
    salario_dia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Salario del Día',
        help_text='Salario normal del trabajador este día'
    )
    tarifa_hora_extra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Tarifa Hora Extra',
        help_text='Tarifa por hora extra este día'
    )

    # Horarios
    hora_entrada = models.TimeField(verbose_name='Hora de Entrada')
    hora_salida = models.TimeField(null=True, blank=True, verbose_name='Hora de Salida')
    
    # Horas calculadas automáticamente
    horas_normales = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Horas Normales'
    )
    horas_extras = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Horas Extras'
    )
    horas_totales = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Horas Totales'
    )

    # Horas especiales
    horas_festivas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Horas en Festivo',
        help_text='Horas trabajadas en día festivo'
    )
    horas_nocturnas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Horas Nocturnas',
        help_text='Horas trabajadas entre 6pm y 6am'
    )
    salario_hora_festiva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Tarifa Hora Festiva',
        help_text='Tarifa especial por hora en festivo'
    )
    salario_hora_nocturna = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Tarifa Hora Nocturna',
        help_text='Tarifa especial por hora nocturna'
    )
    es_dia_festivo = models.BooleanField(
        default=False,
        verbose_name='Es Día Festivo',
        help_text='Indica si este día es festivo'
    )
    
    # Estado y control
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='abierto',
        verbose_name='Estado'
    )
    llego_tarde = models.BooleanField(default=False, verbose_name='Llegó Tarde')
    minutos_tarde = models.IntegerField(default=0, help_text='Minutos de tardanza')
    salio_temprano = models.BooleanField(default=False, verbose_name='Salió Temprano')
    
    # Geolocalización
    latitud_entrada = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Latitud Entrada'
    )
    longitud_entrada = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Longitud Entrada'
    )
    latitud_salida = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Latitud Salida'
    )
    longitud_salida = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Longitud Salida'
    )
    
    # Validación de ubicación
    ubicacion_entrada_valida = models.BooleanField(
        default=True,
        verbose_name='Ubicación de Entrada Válida'
    )
    ubicacion_salida_valida = models.BooleanField(
        default=True,
        verbose_name='Ubicación de Salida Válida'
    )
    distancia_entrada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Distancia Entrada (metros)'
    )
    distancia_salida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Distancia Salida (metros)'
    )
    
    # Método de identificación
    metodo_identificacion = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
        default='manual',
        verbose_name='Método de Identificación'
    )
    
    # Información del dispositivo
    dispositivo_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='ID del Dispositivo'
    )
    
    # Auditoría
    registrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_registradas',
        verbose_name='Registrado Por'
    )
    editado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_editadas',
        verbose_name='Editado Por'
    )
    
    # Soft delete
    eliminado = models.BooleanField(default=False, verbose_name='Eliminado')
    
    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    
    # Timestamps
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name='Creado En')
    modificado_en = models.DateTimeField(auto_now=True, verbose_name='Modificado En')
    sincronizado_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Sincronizado En'
    )
    
    class Meta:
        db_table = 'asistencias'
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha', '-hora_entrada']
        unique_together = [['trabajador', 'fecha']]
        indexes = [
            models.Index(fields=['fecha', 'trabajador']),
            models.Index(fields=['proyecto', 'fecha']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"{self.trabajador.nombre_completo} - {self.fecha} ({self.get_estado_display()})"
    
    def get_jornada_normal_horas(self):
        """
        Retorna la cantidad de horas normales según el día de la semana.
        L-J: 8.5h, V: 9h, S: 5h
        """
        dia_semana = self.fecha.weekday()
        
        if 0 <= dia_semana <= 3:  # Lunes a Jueves
            return Decimal('8.50')
        elif dia_semana == 4:  # Viernes
            return Decimal('9.00')
        elif dia_semana == 5:  # Sábado
            return Decimal('5.00')
        else:  # Domingo
            return Decimal('0.00')

    def calcular_horas(self):
        """Calcula las horas trabajadas usando los horarios del proyecto"""
        if not self.hora_entrada:
            self.horas_normales = Decimal('0.00')
            self.horas_extras = Decimal('0.00')
            self.horas_nocturnas = Decimal('0.00')
            self.horas_festivas = Decimal('0.00')
            self.horas_totales = Decimal('0.00')
            return
        
        # Obtener horario del proyecto según día de la semana
        hora_inicio_esperada, hora_fin_esperada, jornada_normal = self.proyecto.obtener_horario_dia(self.fecha)
        
        # Si es domingo, no se trabaja
        if hora_inicio_esperada is None:
            self.horas_normales = Decimal('0.00')
            self.horas_extras = Decimal('0.00')
            self.horas_festivas = Decimal('0.00')
            self.horas_nocturnas = Decimal('0.00')
            self.horas_totales = Decimal('0.00')
            return
        
        # Si el turno está abierto, usar hora actual como salida temporal
        if self.estado == 'abierto' or not self.hora_salida:
            hora_salida_calculo = timezone.now().time()
        else:
            hora_salida_calculo = self.hora_salida
        
        # Convertir a datetime para cálculos
        entrada_dt = datetime.combine(self.fecha, self.hora_entrada)
        salida_dt = datetime.combine(self.fecha, hora_salida_calculo)
        
        # Si la salida es menor que la entrada, asumir día siguiente
        if salida_dt <= entrada_dt:
            salida_dt += timedelta(days=1)
        
        # Calcular total de horas trabajadas
        diferencia = salida_dt - entrada_dt
        total_horas = Decimal(str(diferencia.total_seconds() / 3600))
        
        # Calcular horas normales y extras
        jornada_normal_decimal = Decimal(str(jornada_normal))
        
        if total_horas <= jornada_normal_decimal:
            self.horas_normales = total_horas
            self.horas_extras = Decimal('0.00')
        else:
            self.horas_normales = jornada_normal_decimal
            self.horas_extras = total_horas - jornada_normal_decimal
        
        # Calcular horas nocturnas (18:00 - 06:00)
        self.horas_nocturnas = self._calcular_horas_nocturnas(entrada_dt, salida_dt)
        
        # Calcular horas festivas si aplica
        if self.es_dia_festivo:
            self.horas_festivas = total_horas
        else:
            self.horas_festivas = Decimal('0.00')
        
        # Total
        self.horas_totales = total_horas
        
        # Redondear a 2 decimales
        self.horas_normales = self.horas_normales.quantize(Decimal('0.01'))
        self.horas_extras = self.horas_extras.quantize(Decimal('0.01'))
        self.horas_nocturnas = self.horas_nocturnas.quantize(Decimal('0.01'))
        self.horas_festivas = self.horas_festivas.quantize(Decimal('0.01'))
        self.horas_totales = self.horas_totales.quantize(Decimal('0.01'))

    def _calcular_horas_nocturnas(self, entrada_dt, salida_dt):
        """Calcula horas trabajadas entre 18:00 (6 PM) y 06:00 (6 AM)"""
        horas_nocturnas = 0
        hora_actual = entrada_dt
        
        while hora_actual < salida_dt:
            hora_del_dia = hora_actual.hour
            
            if hora_del_dia >= 18 or hora_del_dia < 6:
                siguiente_hora = hora_actual + timedelta(hours=1)
                siguiente_hora = siguiente_hora.replace(minute=0, second=0, microsecond=0)
                
                if siguiente_hora > salida_dt:
                    siguiente_hora = salida_dt
                
                tiempo_nocturno = (siguiente_hora - hora_actual).total_seconds() / 3600
                horas_nocturnas += tiempo_nocturno
            
            hora_actual += timedelta(hours=1)
            hora_actual = hora_actual.replace(minute=0, second=0, microsecond=0)
        
        return Decimal(str(horas_nocturnas))

    def verificar_llegada_tarde(self):
        """Verificar si el trabajador llegó tarde según horario del proyecto"""
        if not self.hora_entrada:
            self.llego_tarde = False
            self.minutos_tarde = 0
            return
        
        # Obtener horario del proyecto
        hora_inicio_esperada, _, _ = self.proyecto.obtener_horario_dia(self.fecha)
        
        if not hora_inicio_esperada:
            self.llego_tarde = False
            self.minutos_tarde = 0
            return
        
        # Aplicar tolerancia
        tolerancia = self.proyecto.minutos_tolerancia_entrada or 0
        
        # Convertir a datetime para comparación
        entrada = datetime.combine(self.fecha, self.hora_entrada)
        inicio_esperado = datetime.combine(self.fecha, hora_inicio_esperada)
        inicio_con_tolerancia = inicio_esperado + timedelta(minutes=tolerancia)
        
        if entrada > inicio_con_tolerancia:
            self.llego_tarde = True
            minutos_diferencia = (entrada - inicio_esperado).total_seconds() / 60
            self.minutos_tarde = int(minutos_diferencia)
        else:
            self.llego_tarde = False
            self.minutos_tarde = 0

    def verificar_salida_temprana(self):
        """Verificar si el trabajador salió antes de hora"""
        if not self.hora_salida:
            self.salio_temprano = False
            return
        
        # Obtener horario del proyecto
        _, hora_fin_esperada, _ = self.proyecto.obtener_horario_dia(self.fecha)
        
        if not hora_fin_esperada:
            self.salio_temprano = False
            return
        
        # Aplicar tolerancia
        tolerancia = self.proyecto.minutos_tolerancia_salida or 0
        
        # Convertir a datetime para comparación
        salida = datetime.combine(self.fecha, self.hora_salida)
        fin_esperado = datetime.combine(self.fecha, hora_fin_esperada)
        fin_con_tolerancia = fin_esperado - timedelta(minutes=tolerancia)
        
        self.salio_temprano = salida < fin_con_tolerancia

    def cerrar_turno(self, hora_salida=None):
        """Cierra el turno y calcula las horas trabajadas"""
        if not hora_salida:
            hora_salida = timezone.now().time()
        
        self.hora_salida = hora_salida
        self.estado = 'cerrado'
        self.save()

    @property
    def duracion_jornada(self):
        """Retorna la duración de la jornada en formato legible"""
        if not self.hora_salida:
            return "En curso"
        
        horas = int(self.horas_totales)
        minutos = int((self.horas_totales - horas) * 60)
        return f"{horas}h {minutos}min"

    @property
    def puede_editar(self):
        """Solo se pueden editar asistencias de los últimos 2 días"""
        if self.eliminado:
            return False
        
        hoy = timezone.now().date()
        return self.fecha >= (hoy - timedelta(days=2))

    @property
    def motivo_no_editable(self):
        """Retorna el motivo por el cual no se puede editar"""
        if self.eliminado:
            return "La asistencia ha sido eliminada"
        
        hoy = timezone.now().date()
        dias_diferencia = (hoy - self.fecha).days
        
        if dias_diferencia > 2:
            return f"Han pasado {dias_diferencia} días desde el registro. Solo se pueden editar asistencias de los últimos 2 días."
        
        return "Puede ser editada"

    @property
    def dias_desde_registro(self):
        """Calcula cuántos días han pasado desde el registro"""
        hoy = timezone.now().date()
        return (hoy - self.fecha).days

    @property
    def puede_eliminar(self):
        """Verifica si la asistencia puede ser eliminada"""
        return not self.eliminado

    def save(self, *args, **kwargs):
        """Override del save para cálculos automáticos"""
        # Copiar salarios del trabajador si no existen
        if not self.pk and self.trabajador:
            if not self.salario_dia:
                self.salario_dia = self.trabajador.salario_normal or Decimal('0.00')
            if not self.tarifa_hora_extra:
                self.tarifa_hora_extra = self.trabajador.tarifa_hora_extra or Decimal('0.00')
            if not self.salario_hora_festiva:
                self.salario_hora_festiva = self.trabajador.salario_festivo or Decimal('0.00')
            if not self.salario_hora_nocturna:
                self.salario_hora_nocturna = self.trabajador.salario_nocturno or Decimal('0.00')
        
        # Verificar llegada tarde
        if self.hora_entrada:
            self.verificar_llegada_tarde()
        
        # Calcular horas y verificar salida temprana
        if self.hora_salida:
            self.verificar_salida_temprana()
        
        self.calcular_horas()
        
        super().save(*args, **kwargs)


class ResumenDiario(models.Model):
    """Modelo para almacenar resúmenes diarios de asistencias"""
    
    trabajador = models.ForeignKey(
        'trabajadores.Trabajador',
        on_delete=models.CASCADE,
        related_name='resumenes_diarios'
    )
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.CASCADE,
        related_name='resumenes_diarios'
    )
    fecha = models.DateField()
    asistio = models.BooleanField(default=False)
    llego_tarde = models.BooleanField(default=False)
    horas_totales = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    horas_extras = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        db_table = 'resumen_diario'
        verbose_name = 'Resumen Diario'
        verbose_name_plural = 'Resúmenes Diarios'
        unique_together = [['trabajador', 'fecha']]
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.trabajador.nombre_completo} - {self.fecha}"
        