from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import datetime, timedelta, time
from decimal import Decimal
from apps.usuarios.models import Usuario


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

    # 1. VALIDACIÓN POR SUPERVISOR
    validado = models.BooleanField(
        default=False,
        verbose_name='Validado',
        help_text='Indica si el supervisor validó esta asistencia'
    )
    validado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_validadas',
        verbose_name='Validado Por'
    )
    validado_fecha = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Validación'
    )
    observaciones_validacion = models.TextField(
        blank=True,
        verbose_name='Observaciones de Validación',
        help_text='Comentarios del supervisor al validar'
    )

    # 2. CORRECCIÓN DE MARCACIONES
    fue_corregida = models.BooleanField(
        default=False,
        verbose_name='Fue Corregida',
        help_text='Indica si esta asistencia fue corregida por un supervisor'
    )
    corregida_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_corregidas',
        verbose_name='Corregida Por'
    )
    corregida_fecha = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Corrección'
    )
    motivo_correccion = models.TextField(
        blank=True,
        verbose_name='Motivo de Corrección',
        help_text='Explica por qué se corrigió la marcación'
    )
    hora_entrada_original = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora Entrada Original',
        help_text='Hora de entrada antes de la corrección'
    )
    hora_salida_original = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora Salida Original',
        help_text='Hora de salida antes de la corrección'
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
        #return f"{self.trabajador.nombre_completo} - {self.fecha} ({self.get_estado_display()})"
        entrada = self.hora_entrada.strftime('%H:%M') if self.hora_entrada else 'Sin entrada'
        salida = self.hora_salida.strftime('%H:%M') if self.hora_salida else 'Sin salida'
        tarde = " (TARDE)" if self.llego_tarde else ""
        return f"{self.trabajador.nombre_completo} - {self.proyecto.nombre} - {self.fecha} ({entrada}-{salida}){tarde}"


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
        resultado_horario = self.proyecto.obtener_horario_dia(self.fecha)
        if len(resultado_horario) == 4:
            hora_inicio_esperada, hora_fin_esperada, jornada_normal, descanso_horas = resultado_horario
        else:
            hora_inicio_esperada, hora_fin_esperada, jornada_normal = resultado_horario
            descanso_horas = 0
        
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
        
        # ============================================================
        # 🔧 CORRECCIÓN: Detectar turno nocturno correctamente
        # ============================================================
        
        # Calcular diferencia inicial en segundos
        diferencia_segundos = (salida_dt - entrada_dt).total_seconds()
        
        # CASO 1: Si la diferencia es negativa, cruzó medianoche
        if diferencia_segundos < 0:
            salida_dt += timedelta(days=1)
            diferencia_segundos = (salida_dt - entrada_dt).total_seconds()
        
        # CASO 2: Si la diferencia es muy pequeña (< 2 minutos), es error de marcación
        elif diferencia_segundos < 120:
            self.horas_normales = Decimal('0.00')
            self.horas_extras = Decimal('0.00')
            self.horas_nocturnas = Decimal('0.00')
            self.horas_festivas = Decimal('0.00')
            self.horas_totales = Decimal('0.00')
            return
        
        # Calcular horas totales
        total_horas = Decimal(str(diferencia_segundos / 3600))
        
        # ============================================================
        # VALIDACIÓN: Si resultan más de 24h, es un error
        # ============================================================
        if total_horas > 24:
            self.horas_normales = Decimal('0.00')
            self.horas_extras = Decimal('0.00')
            self.horas_nocturnas = Decimal('0.00')
            self.horas_festivas = Decimal('0.00')
            self.horas_totales = Decimal('0.00')
            
            nota_error = f"[ERROR AUTO] Turno de {float(total_horas):.1f}h detectado. Verificar fechas."
            if self.observaciones:
                if nota_error not in self.observaciones:
                    self.observaciones += f"\n{nota_error}"
            else:
                self.observaciones = nota_error
            
            return
        
        # ============================================================
        # CÁLCULO DE HORAS NORMALES Y EXTRAS
        # ============================================================
        jornada_normal_decimal = Decimal(str(jornada_normal))
        
        if total_horas <= jornada_normal_decimal:
            self.horas_normales = total_horas
            self.horas_extras = Decimal('0.00')
        else:
            self.horas_normales = jornada_normal_decimal
            self.horas_extras = total_horas - jornada_normal_decimal
        
        # ============================================================
        # CÁLCULO DE HORAS NOCTURNAS (18:00 - 06:00)
        # ============================================================
        horas_nocturnas_calculadas = Decimal('0.00')
        hora_actual = entrada_dt
        
        while hora_actual < salida_dt:
            hora_del_dia = hora_actual.hour
            
            # Si está en horario nocturno
            if hora_del_dia >= 18 or hora_del_dia < 6:
                siguiente_hora = hora_actual + timedelta(hours=1)
                siguiente_hora = siguiente_hora.replace(minute=0, second=0, microsecond=0)
                
                if siguiente_hora > salida_dt:
                    siguiente_hora = salida_dt
                
                tiempo_nocturno = (siguiente_hora - hora_actual).total_seconds() / 3600
                horas_nocturnas_calculadas += Decimal(str(tiempo_nocturno))
            
            hora_actual += timedelta(hours=1)
            hora_actual = hora_actual.replace(minute=0, second=0, microsecond=0)
        
        self.horas_nocturnas = horas_nocturnas_calculadas
        
        # ============================================================
        # HORAS FESTIVAS
        # ============================================================
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

    def verificar_llegada_tarde(self):
        """Verificar si el trabajador llegó tarde según horario del proyecto"""
        if not self.hora_entrada:
            self.llego_tarde = False
            self.minutos_tarde = 0
            return
        
        # Obtener horario del proyecto
        resultado_horario = self.proyecto.obtener_horario_dia(self.fecha)
        hora_inicio_esperada = resultado_horario[0]
        
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
        resultado_horario = self.proyecto.obtener_horario_dia(self.fecha)
        hora_fin_esperada = resultado_horario[1] if len(resultado_horario) > 1 else None
        
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
            hora_salida = timezone.localtime().time()
        
        self.hora_salida = hora_salida
        self.estado = 'cerrado'
        self.save()

    def validar(self, usuario, observaciones=''):
        """
        Valida la asistencia por parte del supervisor
        
        Args:
            usuario: Usuario que valida (debe ser supervisor)
            observaciones: Observaciones opcionales
        
        Returns:
            bool: True si se validó exitosamente
        
        Raises:
            ValueError: Si la asistencia ya está validada o no está cerrada
        """
        from django.utils import timezone
        
        # Validaciones
        if self.validado:
            raise ValueError('Esta asistencia ya fue validada')
        
        if self.estado != 'cerrado':
            raise ValueError('Solo se pueden validar asistencias cerradas')
        
        if self.eliminado:
            raise ValueError('No se puede validar una asistencia eliminada')
        
        # Verificar que el usuario es supervisor del proyecto
        if not usuario.es_administrador() and self.proyecto.supervisor != usuario:
            raise ValueError('Solo el supervisor del proyecto puede validar esta asistencia')
        
        # Validar
        self.validado = True
        self.validado_por = usuario
        self.validado_fecha = timezone.now()
        self.observaciones_validacion = observaciones
        self.estado = 'validado'
        self.editado_por = usuario
        self.save()
        
        return True


    def rechazar(self, usuario, motivo):
        """
        Rechaza la asistencia
        
        Args:
            usuario: Usuario que rechaza (debe ser supervisor)
            motivo: Motivo del rechazo (obligatorio)
        
        Returns:
            bool: True si se rechazó exitosamente
        
        Raises:
            ValueError: Si el motivo está vacío o la asistencia ya fue validada
        """
        from django.utils import timezone
        
        # Validaciones
        if not motivo or motivo.strip() == '':
            raise ValueError('Debe especificar un motivo para rechazar la asistencia')
        
        if self.validado:
            raise ValueError('No se puede rechazar una asistencia ya validada')
        
        if self.eliminado:
            raise ValueError('No se puede rechazar una asistencia eliminada')
        
        # Verificar permisos
        if not usuario.es_administrador() and self.proyecto.supervisor != usuario:
            raise ValueError('Solo el supervisor del proyecto puede rechazar esta asistencia')
        
        # Rechazar
        self.estado = 'rechazado'
        self.observaciones_validacion = f'[RECHAZADA] {motivo}'
        self.editado_por = usuario
        self.save()
        
        return True


    def corregir(self, usuario, nueva_hora_entrada=None, nueva_hora_salida=None, motivo=''):
        """
        Corrige las marcaciones de entrada/salida
        
        Args:
            usuario: Usuario que corrige (debe ser supervisor)
            nueva_hora_entrada: Nueva hora de entrada (opcional)
            nueva_hora_salida: Nueva hora de salida (opcional)
            motivo: Motivo de la corrección (obligatorio)
        
        Returns:
            bool: True si se corrigió exitosamente
        
        Raises:
            ValueError: Si no hay cambios o el motivo está vacío
        """
        from django.utils import timezone
        
        # Validaciones
        if not motivo or motivo.strip() == '':
            raise ValueError('Debe especificar un motivo para la corrección')
        
        if not nueva_hora_entrada and not nueva_hora_salida:
            raise ValueError('Debe especificar al menos una hora para corregir')
        
        if self.eliminado:
            raise ValueError('No se puede corregir una asistencia eliminada')
        
        # Verificar permisos
        if not usuario.es_administrador() and self.proyecto.supervisor != usuario:
            raise ValueError('Solo el supervisor del proyecto puede corregir esta asistencia')
        
        # Guardar valores originales (solo la primera vez)
        if not self.fue_corregida:
            self.hora_entrada_original = self.hora_entrada
            self.hora_salida_original = self.hora_salida
        
        # Aplicar correcciones
        if nueva_hora_entrada:
            self.hora_entrada = nueva_hora_entrada
        
        if nueva_hora_salida:
            self.hora_salida = nueva_hora_salida
        
        # Si hay nueva hora de salida, recalcular horas
        if nueva_hora_salida and self.hora_entrada:
            self._calcular_horas()
        
        # Registrar corrección
        self.fue_corregida = True
        self.corregida_por = usuario
        self.corregida_fecha = timezone.now()
        
        # Agregar al motivo si ya había uno previo
        if self.motivo_correccion:
            self.motivo_correccion += f'\n\n[{timezone.now().strftime("%Y-%m-%d %H:%M")}] {motivo}'
        else:
            self.motivo_correccion = motivo
        
        self.editado_por = usuario
        self.save()
        
        return True


    def puede_ser_validada(self):
        """
        Verifica si la asistencia puede ser validada
        
        Returns:
            bool: True si puede ser validada
        """
        return (
            self.estado == 'cerrado' and
            not self.validado and
            not self.eliminado
        )


    @property
    def necesita_validacion(self):
        """
        Indica si la asistencia necesita validación
        
        Returns:
            bool: True si necesita validación
        """
        return self.estado == 'cerrado' and not self.validado and not self.eliminado


    @property
    def duracion_jornada(self):
        """Retorna la duración de la jornada en formato legible"""
        if not self.hora_salida:
            return "En curso"
        
        horas = int(self.horas_totales)
        minutos = int((self.horas_totales - horas) * 60)
        return f"{horas}h {minutos}min"

########! se quita la validacion mientras se sale a produccion
    # @property
    # def puede_editar(self):
    #     """Solo se pueden editar asistencias de los últimos 2 días"""
    #     if self.eliminado:
    #         return False
        
    #     hoy = timezone.now().date()
    #     return self.fecha >= (hoy - timedelta(days=2))
    #     #return True
    @property
    def puede_editar(self):
        """Permitir edición sin restricción de días (temporal para pre-producción)"""
        if self.eliminado:
            return False
        return True
    #! se comenta  mientras se prueba el sistema y se sale a producciom        
    # @property
    # def motivo_no_editable(self):
    #     """Retorna el motivo por el cual no se puede editar"""
    #     if self.eliminado:
    #         return "La asistencia ha sido eliminada"
        
    #     hoy = timezone.now().date()
    #     dias_diferencia = (hoy - self.fecha).days
        
    #     if dias_diferencia > 2:
    #         return f"Han pasado {dias_diferencia} días desde el registro. Solo se pueden editar asistencias de los últimos 2 días."
        
    #     return "Puede ser editada"
    @property
    def motivo_no_editable(self):
        """Retorna el motivo por el cual no se puede editar"""
        if self.eliminado:
            return "La asistencia ha sido eliminada"
        return None

    @property
    def dias_desde_registro(self):
        """Calcula cuántos días han pasado desde el registro"""
        hoy = timezone.now().date()
        return (hoy - self.fecha).days

    @property
    def puede_eliminar(self):
        """Verifica si la asistencia puede ser eliminada"""
        return not self.eliminado

    def validar_dia_laboral(self):
        """
        Valida si la fecha de asistencia es un día laboral del proyecto
        
        Returns:
            tuple: (es_valido, mensaje)
        """
        if not self.fecha or not self.proyecto:
            return True, "Sin información para validar"
        
        es_laboral, mensaje = self.proyecto.es_dia_laboral(self.fecha)
        
        if not es_laboral:
            return False, f"⚠️ {mensaje}. Los días laborales son: {self.proyecto.get_dias_laborales_nombres()}"
        
        return True, "Día laboral válido"


    def get_comparacion_horario(self):
        """
        Retorna comparación entre horario esperado y real
        
        Returns:
            dict: Información de comparación de horarios
        """
        if not self.proyecto:
            return {}
        
        return {
            'entrada_esperada': self.proyecto.hora_entrada_esperada,
            'entrada_real': self.hora_entrada,
            'salida_esperada': self.proyecto.hora_salida_esperada,
            'salida_real': self.hora_salida,
            'tolerancia_minutos': self.proyecto.minutos_tolerancia,
            'llego_tarde': self.llego_tarde,
            'minutos_tarde': self.minutos_tarde,
            'horas_extras': self.horas_extras,
            'dentro_tolerancia': self.minutos_tarde <= self.proyecto.minutos_tolerancia if self.llego_tarde else True,
        }


    def calcular_minutos_trabajados(self):
        """
        Calcula minutos totales trabajados
        
        Returns:
            int: Minutos trabajados
        """
        if not self.hora_entrada or not self.hora_salida:
            return 0
        
        from datetime import datetime, timedelta
        
        entrada = datetime.combine(datetime.today(), self.hora_entrada)
        salida = datetime.combine(datetime.today(), self.hora_salida)
        
        if salida < entrada:
            salida += timedelta(days=1)
        
        diferencia = salida - entrada
        return int(diferencia.total_seconds() / 60)


    def get_resumen_turno(self):
        """
        Retorna resumen completo del turno
        
        Returns:
            dict: Resumen con todos los datos del turno
        """
        return {
            'trabajador': self.trabajador.nombre_completo,
            'proyecto': self.proyecto.nombre,
            'fecha': self.fecha,
            'es_dia_laboral': self.proyecto.es_dia_laboral(self.fecha)[0] if self.fecha else False,
            'horario_proyecto': self.proyecto.get_horario_display(),
            'entrada_real': self.hora_entrada.strftime('%H:%M') if self.hora_entrada else None,
            'salida_real': self.hora_salida.strftime('%H:%M') if self.hora_salida else None,
            'llego_tarde': self.llego_tarde,
            'minutos_tarde': self.minutos_tarde,
            'horas_trabajadas': self.horas_totales,
            'horas_normales': self.horas_normales,
            'horas_extras': self.horas_extras,
            'duracion': self.duracion_jornada,
            'estado': self.get_estado_display(),
            'validado': self.validado,
        }


    @property
    def alerta_dia_no_laboral(self):
        """
        Indica si la asistencia es en un día no laboral
        
        Returns:
            bool: True si es día no laboral
        """
        if not self.fecha or not self.proyecto:
            return False
        
        es_laboral, _ = self.proyecto.es_dia_laboral(self.fecha)
        return not es_laboral


    @property
    def excede_horas_jornada(self):
        """
        Indica si las horas trabajadas exceden la jornada normal
        
        Returns:
            bool: True si excede la jornada
        """
        if not self.horas_totales or not self.proyecto:
            return False
        
        return self.horas_totales > float(self.proyecto.horas_jornada)


    @property
    def dentro_tolerancia_entrada(self):
        """
        Indica si la entrada está dentro de la tolerancia
        
        Returns:
            bool: True si está dentro de tolerancia
        """
        if not self.llego_tarde:
            return True
        
        return self.minutos_tarde <= self.proyecto.minutos_tolerancia


    @property
    def mensaje_horario(self):
        """
        Genera mensaje descriptivo del horario
        
        Returns:
            str: Mensaje sobre el cumplimiento de horario
        """
        if not self.hora_entrada:
            return "Sin registro de entrada"
        
        mensajes = []
        
        # Entrada
        if self.llego_tarde:
            if self.dentro_tolerancia_entrada:
                mensajes.append(f"Llegó {self.minutos_tarde} min tarde (dentro de tolerancia)")
            else:
                mensajes.append(f"Llegó {self.minutos_tarde} min tarde")
        else:
            mensajes.append("Llegó puntual")
        
        # Salida
        if self.hora_salida:
            if self.horas_extras > 0:
                mensajes.append(f"Trabajó {self.horas_extras:.1f}h extras")
            else:
                mensajes.append("Salió en horario normal")
        
        # Día no laboral
        if self.alerta_dia_no_laboral:
            mensajes.append("⚠️ Día no laboral")
        
        return " | ".join(mensajes)

    def save(self, *args, **kwargs):
        """
        Método save mejorado con cálculos automáticos basados en horarios del proyecto POR DÍA
        """
        from datetime import datetime, timedelta
        
        if self.hora_entrada and self.proyecto and self.fecha:
            # ===== 1. OBTENER HORARIO DEL DÍA ESPECÍFICO =====
            resultado_horario = self.proyecto.obtener_horario_dia(self.fecha)
            if len(resultado_horario) == 4:
                hora_inicio_esperada, hora_fin_esperada, jornada_normal, descanso_horas = resultado_horario
            else:
                hora_inicio_esperada, hora_fin_esperada, jornada_normal = resultado_horario
                descanso_horas = 0
            
            # Si es día no laboral (domingo sin horario)
            if hora_inicio_esperada is None:
                self.minutos_tarde = 0
                self.llego_tarde = False
                
                # Si hay hora de salida, calcular horas trabajadas (todas son extras)
                if self.hora_salida:
                    entrada_dt = datetime.combine(self.fecha, self.hora_entrada)
                    salida_dt = datetime.combine(self.fecha, self.hora_salida)
                    
                    # Si la salida es antes que la entrada, cruzó medianoche
                    if salida_dt < entrada_dt:
                        salida_dt += timedelta(days=1)
                    
                    diferencia = salida_dt - entrada_dt
                    total_horas = Decimal(str(diferencia.total_seconds() / 3600))
                    
                    # Validar que no sea negativo o absurdo
                    if total_horas < 0 or total_horas > 24:
                        total_horas = Decimal('0.00')
                    
                    self.horas_totales = total_horas.quantize(Decimal('0.01'))
                    self.horas_normales = Decimal('0.00')  # No hay jornada normal en día no laboral
                    self.horas_extras = self.horas_totales  # Todas las horas son extras
                else:
                    self.horas_totales = Decimal('0.00')
                    self.horas_normales = Decimal('0.00')
                    self.horas_extras = Decimal('0.00')
                
                super().save(*args, **kwargs)
                return
            
            # ===== 2. CONVERTIR HORARIOS DE STRING A TIME =====
            # Los horarios están en formato "08:00 AM" o "05:00 PM"
            def parse_hora_12h(hora_str):
                """Convierte '08:00 AM' o '05:00 PM' a objeto time"""
                if not hora_str:
                    return None
                try:
                    # Si ya es un objeto time
                    if hasattr(hora_str, 'hour'):
                        return hora_str
                    # Si es string en formato 12h
                    hora_str = hora_str.strip().upper()
                    return datetime.strptime(hora_str, '%I:%M %p').time()
                except:
                    try:
                        # Intentar formato 24h
                        return datetime.strptime(hora_str, '%H:%M').time()
                    except:
                        return None
            
            hora_inicio_time = parse_hora_12h(hora_inicio_esperada)
            hora_fin_time = parse_hora_12h(hora_fin_esperada)
            
            # ===== 3. CALCULAR LLEGADA TARDE =====
            if hora_inicio_time:
                tolerancia = self.proyecto.minutos_tolerancia_entrada or self.proyecto.minutos_tolerancia or 15
                
                entrada_dt = datetime.combine(self.fecha, self.hora_entrada)
                inicio_esperado_dt = datetime.combine(self.fecha, hora_inicio_time)
                inicio_con_tolerancia = inicio_esperado_dt + timedelta(minutes=tolerancia)
                
                if entrada_dt > inicio_con_tolerancia:
                    self.llego_tarde = True
                    self.minutos_tarde = int((entrada_dt - inicio_esperado_dt).total_seconds() / 60)
                else:
                    self.llego_tarde = False
                    self.minutos_tarde = 0
            
            # ===== 4. CALCULAR HORAS TRABAJADAS =====
            if self.hora_salida:
                entrada_dt = datetime.combine(self.fecha, self.hora_entrada)
                salida_dt = datetime.combine(self.fecha, self.hora_salida)
                
                # Si la salida es antes que la entrada, cruzó medianoche
                if salida_dt < entrada_dt:
                    salida_dt += timedelta(days=1)
                
                # Calcular horas totales
                diferencia = salida_dt - entrada_dt
                total_horas = Decimal(str(diferencia.total_seconds() / 3600))
                
                # Validar que no sea negativo o absurdo
                if total_horas < 0 or total_horas > 24:
                    total_horas = Decimal('0.00')
                
                self.horas_totales = total_horas.quantize(Decimal('0.01'))
                
                # Restar descanso (almuerzo) de las horas totales
                descanso_decimal = Decimal(str(descanso_horas)) if descanso_horas else Decimal('0.00')
                horas_netas = (self.horas_totales - descanso_decimal).quantize(Decimal('0.01'))
                if horas_netas < Decimal('0.00'):
                    horas_netas = Decimal('0.00')
                
                # Calcular horas normales y extras basado en jornada del día
                jornada_decimal = Decimal(str(jornada_normal))
                
                if horas_netas <= jornada_decimal:
                    self.horas_normales = horas_netas
                    self.horas_extras = Decimal('0.00')
                else:
                    self.horas_normales = jornada_decimal
                    self.horas_extras = (horas_netas - jornada_decimal).quantize(Decimal('0.01'))
            else:
                # Sin hora de salida, no hay horas calculadas
                self.horas_totales = Decimal('0.00')
                self.horas_normales = Decimal('0.00')
                self.horas_extras = Decimal('0.00')
        
        # ===== 5. CERRAR AUTOMÁTICAMENTE SI HAY SALIDA =====
        if self.hora_salida and self.estado == 'abierto':
            self.estado = 'cerrado'
        
        # # ===== 6. CALCULAR DURACIÓN JORNADA =====
        # if self.horas_totales:
        #     horas = int(self.horas_totales)
        #     minutos = int((self.horas_totales - horas) * 60)
        #     self.duracion_jornada = f"{horas}h {minutos}m"
        
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
        