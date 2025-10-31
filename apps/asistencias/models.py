from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import datetime, timedelta, time  # <--- IMPORTADO time
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
    
    # Estado y control
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='abierto',
        verbose_name='Estado'
    )
    llego_tarde = models.BooleanField(default=False, verbose_name='Llegó Tarde')
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
        Basado en el requisito: L-J 7am-4:30pm (8.5h), V 7am-5pm (9h), S 7am-12pm (5h)
        Asumiendo 1 hora de almuerzo para L-J y V.
        """
        dia_semana = self.fecha.weekday()  # Lunes=0, Martes=1, ..., Domingo=6
        
        if 0 <= dia_semana <= 3:  # Lunes a Jueves
            # 7:00 a 16:30 = 9.5 horas. Asumiendo 1h almuerzo = 8.5h
            return Decimal('8.50')
        elif dia_semana == 4:  # Viernes
            # 7:00 a 17:00 = 10 horas. Asumiendo 1h almuerzo = 9h
            return Decimal('9.00')
        elif dia_semana == 5:  # Sábado
            # 7:00 a 12:00 = 5 horas.
            return Decimal('5.00')
        else:  # Domingo
            return Decimal('0.00')

    def calcular_horas(self):
        """
        Calcula las horas normales, extras y totales trabajadas
        basado en la jornada variable.
        """
        if not self.hora_salida:
            self.horas_normales = Decimal('0.00')
            self.horas_extras = Decimal('0.00')
            self.horas_totales = Decimal('0.00')
            return
        
        # Convertir a datetime para cálculos
        entrada = datetime.combine(self.fecha, self.hora_entrada)
        salida = datetime.combine(self.fecha, self.hora_salida)
        
        # Si la salida es menor que la entrada, asumimos que es del día siguiente
        if salida < entrada:
            salida += timedelta(days=1)
        
        # Calcular diferencia en horas
        diferencia = salida - entrada
        total_horas = Decimal(str(diferencia.total_seconds() / 3600))
        
        # Obtener la jornada normal para este día
        HORAS_NORMALES_MAX = self.get_jornada_normal_horas()
        
        if total_horas <= HORAS_NORMALES_MAX:
            self.horas_normales = total_horas
            self.horas_extras = Decimal('0.00')
        else:
            self.horas_normales = HORAS_NORMALES_MAX
            self.horas_extras = total_horas - HORAS_NORMALES_MAX
        
        self.horas_totales = total_horas
    
    def verificar_llegada_tarde(self):
        """Verifica si el trabajador llegó tarde (después de las 7:00 AM)"""
        HORA_LIMITE = time(7, 0)  # 7:00 AM
        
        # Asegurar que hora_entrada sea un objeto time
        hora_entrada_time = self.hora_entrada
        if isinstance(hora_entrada_time, str):
            try:
                hora_entrada_time = datetime.strptime(hora_entrada_time, '%H:%M:%S').time()
            except ValueError:
                hora_entrada_time = datetime.strptime(hora_entrada_time, '%H:%M').time()
        
        self.llego_tarde = hora_entrada_time > HORA_LIMITE
    
    def verificar_salida_temprano(self):
        """
        Verifica si el trabajador salió antes de cumplir la jornada normal.
        El CSV menciona "si hay miinutos de menos, siempre se contabiliza el dia, 
        solo que se pone como la bandera de aviso". Esta es la bandera.
        """
        if self.hora_salida:
            jornada_normal = self.get_jornada_normal_horas()
            # Se marca si salió temprano Y no cumplió la jornada
            self.salio_temprano = self.horas_totales < jornada_normal
        else:
            self.salio_temprano = False
    
    def cerrar_turno(self, hora_salida=None):
        """Cierra el turno y calcula las horas trabajadas"""
        if not hora_salida:
            hora_salida = timezone.now().time()
        
        self.hora_salida = hora_salida
        self.calcular_horas()  # Ya usa la nueva lógica
        self.verificar_salida_temprano()  # Ya usa la nueva lógica
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
        """Determina si la asistencia puede ser editada"""
        # Solo se puede editar si es del día actual o día anterior
        fecha_actual = timezone.now().date()
        diferencia = (fecha_actual - self.fecha).days
        return diferencia <= 1
    
    def save(self, *args, **kwargs):
        """Override del save para cálculos automáticos"""
        # Verificar llegada tarde al crear/actualizar entrada
        if self.hora_entrada:
            self.verificar_llegada_tarde()
        
        # Calcular horas si hay hora de salida
        if self.hora_salida:
            self.calcular_horas()
            self.verificar_salida_temprano()
        
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
    