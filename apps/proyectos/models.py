import os
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.usuarios.models import Usuario
from django.utils.text import slugify
from datetime import time, datetime, timedelta

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
    # Flag para proyecto administrativo (planilla con fórmulas diferentes)
    is_administrativo = models.BooleanField(
        default=False,
        verbose_name='Proyecto Administrativo',
        help_text='Proyecto virtual para personal administrativo (sueldo fijo, no por horas)'
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
    
    radio_ubicacion = models.IntegerField(
        default=100,
        validators=[MinValueValidator(50), MaxValueValidator(500)],
        verbose_name='Radio de Ubicación (metros)',
        help_text='Radio en metros para validar asistencias'
    )
    
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
    
    contratistas = models.ManyToManyField(
        'contratistas.Contratista',
        related_name='proyectos_asignados',
        blank=True,
        verbose_name='Contratistas Asignados'
    )
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

    # Geolocalización
    latitud = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text='Latitud de la ubicación del proyecto'
    )
    longitud = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text='Longitud de la ubicación del proyecto'
    )
    radio_geovalla = models.IntegerField(
        default=150,
        help_text='Radio permitido en metros para validación de asistencias'
    )
    
    # ============================================================
    # HORARIOS INDIVIDUALES POR DÍA (FORMATO 12H - CharField)
    # ============================================================

    # LUNES
    hora_inicio_lunes = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Lunes (formato 12h: 08:00 AM)'
    )
    hora_fin_lunes = models.CharField(
        max_length=10,
        default='05:00 PM',
        help_text='Hora de fin Lunes (formato 12h: 05:00 PM)'
    )

    # MARTES
    hora_inicio_martes = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Martes (formato 12h)'
    )
    hora_fin_martes = models.CharField(
        max_length=10,
        default='05:00 PM',
        help_text='Hora de fin Martes (formato 12h)'
    )

    # MIÉRCOLES
    hora_inicio_miercoles = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Miércoles (formato 12h)'
    )
    hora_fin_miercoles = models.CharField(
        max_length=10,
        default='05:00 PM',
        help_text='Hora de fin Miércoles (formato 12h)'
    )

    # JUEVES
    hora_inicio_jueves = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Jueves (formato 12h)'
    )
    hora_fin_jueves = models.CharField(
        max_length=10,
        default='05:00 PM',
        help_text='Hora de fin Jueves (formato 12h)'
    )

    # VIERNES
    hora_inicio_viernes = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Viernes (formato 12h)'
    )
    hora_fin_viernes = models.CharField(
        max_length=10,
        default='02:00 PM',
        help_text='Hora de fin Viernes (formato 12h)'
    )

    # SÁBADO
    hora_inicio_sabado = models.CharField(
        max_length=10,
        default='08:00 AM',
        help_text='Hora de inicio Sábado (formato 12h)'
    )
    hora_fin_sabado = models.CharField(
        max_length=10,
        default='12:00 PM',
        help_text='Hora de fin Sábado (formato 12h)'
    )

    # DOMINGO
    hora_inicio_domingo = models.CharField(
        max_length=10,
        default='',
        blank=True,
        help_text='Hora de inicio Domingo (formato 12h, opcional)'
    )
    hora_fin_domingo = models.CharField(
        max_length=10,
        default='',
        blank=True,
        help_text='Hora de fin Domingo (formato 12h, opcional)'
    )

    # ============================================================
    # TIEMPO DE DESCANSO/COMIDA POR DÍA (FORMATO H:MM)
    # ============================================================

    # LUNES
    descanso_lunes = models.CharField(
        max_length=10,
        default='1:00',
        help_text='Tiempo de descanso/comida Lunes (formato H:MM, ej: 1:00, 0:30, 1:30)'
    )

    # MARTES
    descanso_martes = models.CharField(
        max_length=10,
        default='1:00',
        help_text='Tiempo de descanso/comida Martes'
    )

    # MIÉRCOLES
    descanso_miercoles = models.CharField(
        max_length=10,
        default='1:00',
        help_text='Tiempo de descanso/comida Miércoles'
    )

    # JUEVES
    descanso_jueves = models.CharField(
        max_length=10,
        default='1:00',
        help_text='Tiempo de descanso/comida Jueves'
    )

    # VIERNES
    descanso_viernes = models.CharField(
        max_length=10,
        default='1:00',
        help_text='Tiempo de descanso/comida Viernes'
    )

    # SÁBADO
    descanso_sabado = models.CharField(
        max_length=10,
        default='0:00',
        help_text='Tiempo de descanso/comida Sábado'
    )

    # DOMINGO
    descanso_domingo = models.CharField(
        max_length=10,
        default='0:00',
        blank=True,
        help_text='Tiempo de descanso/comida Domingo'
    )

    # TOLERANCIAS
    minutos_tolerancia_entrada = models.IntegerField(
        default=15,
        help_text='Minutos de tolerancia para entrada'
    )
    minutos_tolerancia_salida = models.IntegerField(
        default=10,
        help_text='Minutos de tolerancia para salida temprana'
    )

    def _parsear_descanso(self, descanso_str):
        """
        Convierte string de descanso (H:MM) a horas decimales
        Ej: '1:00' -> 1.0, '1:30' -> 1.5, '0:45' -> 0.75
        """
        if not descanso_str:
            return 0
        try:
            partes = descanso_str.split(':')
            horas = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
            return horas + (minutos / 60)
        except:
            return 1.0  # Default 1 hora si hay error

    def obtener_horario_guarda(self, fecha):
        """
        Obtiene el horario del guarda según el día de la semana.
        Retorna: (hora_inicio, hora_fin, turnos_del_dia)
        """
        if not self.tiene_guardas:
            return (None, None, 0)
        
        dia_semana = fecha.weekday()
        
        horarios = {
            0: (self.guarda_hora_inicio_lunes, self.guarda_hora_fin_lunes, self.guarda_turnos_lunes),
            1: (self.guarda_hora_inicio_martes, self.guarda_hora_fin_martes, self.guarda_turnos_martes),
            2: (self.guarda_hora_inicio_miercoles, self.guarda_hora_fin_miercoles, self.guarda_turnos_miercoles),
            3: (self.guarda_hora_inicio_jueves, self.guarda_hora_fin_jueves, self.guarda_turnos_jueves),
            4: (self.guarda_hora_inicio_viernes, self.guarda_hora_fin_viernes, self.guarda_turnos_viernes),
            5: (self.guarda_hora_inicio_sabado, self.guarda_hora_fin_sabado, self.guarda_turnos_sabado),
            6: (self.guarda_hora_inicio_domingo, self.guarda_hora_fin_domingo, self.guarda_turnos_domingo),
        }
        
        hora_inicio, hora_fin, turnos = horarios.get(dia_semana, ('', '', 0))
        
        if not hora_inicio or not hora_fin:
            return (None, None, 0)
        
        return (hora_inicio, hora_fin, turnos)

    def obtener_horario_dia(self, fecha):
        """
        Obtiene el horario laboral según el día de la semana
        Retorna: (hora_inicio, hora_fin, jornada_neta_horas, descanso_horas)
        """
        dia_semana = fecha.weekday()  # 0=Lunes, 1=Martes, ..., 6=Domingo
        
        horarios = {
            0: (self.hora_inicio_lunes, self.hora_fin_lunes, getattr(self, 'descanso_lunes', '1:00')),
            1: (self.hora_inicio_martes, self.hora_fin_martes, getattr(self, 'descanso_martes', '1:00')),
            2: (self.hora_inicio_miercoles, self.hora_fin_miercoles, getattr(self, 'descanso_miercoles', '1:00')),
            3: (self.hora_inicio_jueves, self.hora_fin_jueves, getattr(self, 'descanso_jueves', '1:00')),
            4: (self.hora_inicio_viernes, self.hora_fin_viernes, getattr(self, 'descanso_viernes', '1:00')),
            5: (self.hora_inicio_sabado, self.hora_fin_sabado, getattr(self, 'descanso_sabado', '0:00')),
            6: (self.hora_inicio_domingo, self.hora_fin_domingo, getattr(self, 'descanso_domingo', '0:00')),
        }
        
        hora_inicio, hora_fin, descanso_str = horarios.get(dia_semana, (None, None, '0:00'))
        
        # Si es domingo y no tiene horario configurado
        if dia_semana == 6 and (not hora_inicio or not hora_fin):
            return (None, None, 0, 0)
        
        # Calcular jornada bruta
        jornada_bruta = self._calcular_horas_jornada(hora_inicio, hora_fin)
        
        # Parsear descanso
        descanso_horas = self._parsear_descanso(descanso_str)
        
        # Jornada neta = bruta - descanso
        jornada_neta = max(0, jornada_bruta - descanso_horas)
        
        return (hora_inicio, hora_fin, jornada_neta, descanso_horas)

    def _calcular_horas_jornada(self, hora_inicio_str, hora_fin_str):
        """Calcula las horas de jornada entre dos horarios en formato 12h"""
        if not hora_inicio_str or not hora_fin_str:
            return 0
        
        try:
            def parse_12h(hora_str):
                hora_str = hora_str.strip().upper()
                try:
                    return datetime.strptime(hora_str, '%I:%M %p')
                except:
                    try:
                        return datetime.strptime(hora_str, '%H:%M')
                    except:
                        return None
            
            inicio = parse_12h(hora_inicio_str)
            fin = parse_12h(hora_fin_str)
            
            if inicio and fin:
                diferencia = (fin - inicio).total_seconds() / 3600
                return round(diferencia, 2) if diferencia > 0 else 0
            return 0
        except:
            return 0
            
    # ==================== HORARIOS DE TRABAJO ====================
    hora_entrada_esperada = models.TimeField(
        default=time(8, 0),
        verbose_name='Hora de Entrada Esperada',
        help_text='Hora de entrada esperada para este proyecto (formato 24h)'
    )

    hora_salida_esperada = models.TimeField(
        default=time(17, 0),
        verbose_name='Hora de Salida Esperada',
        help_text='Hora de salida esperada para este proyecto (formato 24h)'
    )

    minutos_tolerancia = models.IntegerField(
        default=15,
        verbose_name='Minutos de Tolerancia',
        help_text='Minutos permitidos de retraso sin marcar como llegada tarde'
    )

    horas_jornada = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        verbose_name='Horas por Jornada',
        help_text='Cantidad de horas diarias de trabajo esperadas'
    )

    # Días laborales (almacenados como string separado por comas)
    # Formato: "1,2,3,4,5" donde 1=Lunes, 2=Martes, ..., 7=Domingo
    dias_laborales = models.CharField(
        max_length=50,
        default='1,2,3,4,5',
        verbose_name='Días Laborales',
        help_text='Días de la semana que se trabaja en este proyecto (1=Lun, 2=Mar, ..., 7=Dom)'
    )

    # ============================================================
    # HORARIOS DE GUARDAS DE SEGURIDAD
    # ============================================================
    
    tiene_guardas = models.BooleanField(
        default=False,
        verbose_name='Tiene Guardas de Seguridad',
        help_text='Activar para configurar horario de guardas'
    )
    
    # LUNES (entrada PM → salida AM día siguiente)
    guarda_hora_inicio_lunes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Lunes (ej: 04:30 PM)'
    )
    guarda_hora_fin_lunes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Martes AM (ej: 07:00 AM)'
    )
    guarda_turnos_lunes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # MARTES
    guarda_hora_inicio_martes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Martes'
    )
    guarda_hora_fin_martes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Miércoles AM'
    )
    guarda_turnos_martes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # MIÉRCOLES
    guarda_hora_inicio_miercoles = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Miércoles'
    )
    guarda_hora_fin_miercoles = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Jueves AM'
    )
    guarda_turnos_miercoles = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # JUEVES
    guarda_hora_inicio_jueves = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Jueves'
    )
    guarda_hora_fin_jueves = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Viernes AM'
    )
    guarda_turnos_jueves = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # VIERNES
    guarda_hora_inicio_viernes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Viernes'
    )
    guarda_hora_fin_viernes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Sábado AM'
    )
    guarda_turnos_viernes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # SÁBADO (puede contar como 2 turnos)
    guarda_hora_inicio_sabado = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Sábado'
    )
    guarda_hora_fin_sabado = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Lunes AM'
    )
    guarda_turnos_sabado = models.IntegerField(
        default=2, help_text='Cantidad de turnos que cuenta (sábado = 2)'
    )
    
    # DOMINGO (normalmente no aplica, el sábado ya cubre hasta lunes)
    guarda_hora_inicio_domingo = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Domingo (opcional)'
    )
    guarda_hora_fin_domingo = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Lunes AM (opcional)'
    )
    guarda_turnos_domingo = models.IntegerField(
        default=0, help_text='Cantidad de turnos Domingo'
    )

    # ============================================================
    # HORARIOS DE GUARDAS DE SEGURIDAD
    # ============================================================
    
    tiene_guardas = models.BooleanField(
        default=False,
        verbose_name='Tiene Guardas de Seguridad',
        help_text='Activar para configurar horario de guardas'
    )
    
    # LUNES (entrada PM → salida AM día siguiente)
    guarda_hora_inicio_lunes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Lunes (ej: 04:30 PM)'
    )
    guarda_hora_fin_lunes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Martes AM (ej: 07:00 AM)'
    )
    guarda_turnos_lunes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # MARTES
    guarda_hora_inicio_martes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Martes'
    )
    guarda_hora_fin_martes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Miércoles AM'
    )
    guarda_turnos_martes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # MIÉRCOLES
    guarda_hora_inicio_miercoles = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Miércoles'
    )
    guarda_hora_fin_miercoles = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Jueves AM'
    )
    guarda_turnos_miercoles = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # JUEVES
    guarda_hora_inicio_jueves = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Jueves'
    )
    guarda_hora_fin_jueves = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Viernes AM'
    )
    guarda_turnos_jueves = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # VIERNES
    guarda_hora_inicio_viernes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Viernes'
    )
    guarda_hora_fin_viernes = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Sábado AM'
    )
    guarda_turnos_viernes = models.IntegerField(
        default=1, help_text='Cantidad de turnos que cuenta este día'
    )
    
    # SÁBADO (puede contar como 2 turnos)
    guarda_hora_inicio_sabado = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Sábado'
    )
    guarda_hora_fin_sabado = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Lunes AM'
    )
    guarda_turnos_sabado = models.IntegerField(
        default=2, help_text='Cantidad de turnos que cuenta (sábado = 2)'
    )
    
    # DOMINGO (normalmente no aplica, el sábado ya cubre hasta lunes)
    guarda_hora_inicio_domingo = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora entrada guarda Domingo (opcional)'
    )
    guarda_hora_fin_domingo = models.CharField(
        max_length=10, default='', blank=True,
        help_text='Hora salida guarda Lunes AM (opcional)'
    )
    guarda_turnos_domingo = models.IntegerField(
        default=0, help_text='Cantidad de turnos Domingo'
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

    def get_dias_laborales_list(self):
        """
        Retorna lista de días laborales como integers
        
        Returns:
            list: Lista de días laborales [1, 2, 3, 4, 5]
        """
        if not self.dias_laborales:
            return [1, 2, 3, 4, 5]  # Default: Lunes a Viernes
        
        try:
            return [int(d.strip()) for d in self.dias_laborales.split(',') if d.strip()]
        except:
            return [1, 2, 3, 4, 5]


    def get_dias_laborales_nombres(self):
        """
        Retorna nombres de los días laborales
        
        Returns:
            str: "Lunes, Martes, Miércoles, Jueves, Viernes"
        """
        dias_dict = {
            1: 'Lunes',
            2: 'Martes',
            3: 'Miércoles',
            4: 'Jueves',
            5: 'Viernes',
            6: 'Sábado',
            7: 'Domingo',
        }
        
        dias = self.get_dias_laborales_list()
        nombres = [dias_dict.get(d, '') for d in dias]
        return ', '.join(nombres)


    def es_dia_laboral(self, fecha):
        """
        Verifica si una fecha es día laboral del proyecto
        
        Args:
            fecha: date object o datetime
        
        Returns:
            tuple: (bool, str) - (es_laboral, mensaje)
        """
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        
        # 1=Lunes, 2=Martes, ..., 7=Domingo
        dia_semana = fecha.isoweekday()
        
        dias_laborales = self.get_dias_laborales_list()
        
        if dia_semana in dias_laborales:
            return True, "Día laboral"
        else:
            dias_dict = {
                1: 'Lunes', 2: 'Martes', 3: 'Miércoles',
                4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'
            }
            dia_nombre = dias_dict.get(dia_semana, 'Desconocido')
            return False, f"El {dia_nombre} no es día laboral en este proyecto"


    def calcular_llegada_tarde(self, hora_entrada_real):
        """
        Calcula si hubo llegada tarde y cuántos minutos
        
        Args:
            hora_entrada_real: time object con la hora real de entrada
        
        Returns:
            tuple: (minutos_tarde, llego_tarde)
                - minutos_tarde (int): Minutos de retraso efectivos (descontando tolerancia)
                - llego_tarde (bool): True si llegó tarde después de aplicar tolerancia
        """
        if not hora_entrada_real or not self.hora_entrada_esperada:
            return 0, False
        
        # Convertir a datetime para calcular diferencia
        entrada_esperada = datetime.combine(datetime.today(), self.hora_entrada_esperada)
        entrada_real = datetime.combine(datetime.today(), hora_entrada_real)
        
        # Si llegó antes o a tiempo
        if entrada_real <= entrada_esperada:
            return 0, False
        
        # Calcular minutos de retraso
        diferencia = entrada_real - entrada_esperada
        minutos_retraso_total = int(diferencia.total_seconds() / 60)
        
        # Aplicar tolerancia
        if minutos_retraso_total <= self.minutos_tolerancia:
            return 0, False  # Dentro de la tolerancia
        
        # Retraso efectivo (descontando tolerancia)
        minutos_tarde_efectivos = minutos_retraso_total - self.minutos_tolerancia
        
        return minutos_tarde_efectivos, True


    def calcular_horas_extras(self, hora_salida_real):
        """
        Calcula horas extras trabajadas
        
        Args:
            hora_salida_real: time object con la hora real de salida
        
        Returns:
            float: Horas extras trabajadas (puede ser 0)
        """
        if not hora_salida_real or not self.hora_salida_esperada:
            return 0.0
        
        # Convertir a datetime para calcular diferencia
        salida_esperada = datetime.combine(datetime.today(), self.hora_salida_esperada)
        salida_real = datetime.combine(datetime.today(), hora_salida_real)
        
        # Si salió antes o a la hora esperada, no hay extras
        if salida_real <= salida_esperada:
            return 0.0
        
        # Calcular horas extras
        diferencia = salida_real - salida_esperada
        horas_extras = diferencia.total_seconds() / 3600
        
        return round(horas_extras, 2)


    def calcular_horas_trabajadas(self, hora_entrada, hora_salida):
        """
        Calcula el total de horas trabajadas en el turno
        
        Args:
            hora_entrada: time object
            hora_salida: time object
        
        Returns:
            float: Horas totales trabajadas
        """
        if not hora_entrada or not hora_salida:
            return 0.0
        
        entrada = datetime.combine(datetime.today(), hora_entrada)
        salida = datetime.combine(datetime.today(), hora_salida)
        
        # Si la salida es al día siguiente (después de medianoche)
        if salida < entrada:
            salida += timedelta(days=1)
        
        diferencia = salida - entrada
        horas = diferencia.total_seconds() / 3600
        
        return round(horas, 2)


    def get_horario_display(self):
        """
        Retorna el horario en formato legible
        
        Returns:
            str: "08:00 - 17:00 (8.0h)"
        """
        entrada = self.hora_entrada_esperada.strftime('%H:%M')
        salida = self.hora_salida_esperada.strftime('%H:%M')
        return f"{entrada} - {salida} ({self.horas_jornada}h)"

    @property
    def trabajadores_activos_count(self):
        return self.trabajadores.filter(eliminado=False, estado='activo').count()

    @property
    def tiene_horario_configurado(self):
        """
        Verifica si el proyecto tiene horarios configurados
        
        Returns:
            bool: True si tiene horarios válidos
        """
        return (
            self.hora_entrada_esperada is not None and
            self.hora_salida_esperada is not None and
            self.horas_jornada > 0
        )

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

    # ======================================================
    # NORMALIZACIÓN AUTOMÁTICA DE COORDENADAS
    # ======================================================
    def save(self, *args, **kwargs):
        # Si vienen coordenadas tipo: "4.7110000,-74.0721000"
        if self.ubicacion_coordenadas:
            coords = self.ubicacion_coordenadas.strip()

            if ',' in coords:
                try:
                    lat_str, lon_str = coords.split(',')

                    lat = float(lat_str.strip())
                    lon = float(lon_str.strip())

                    self.latitud = lat
                    self.longitud = lon

                except Exception as e:
                    # No romper guardado por error de formato
                    print(f"[GEO NORMALIZE ERROR] {coords} -> {e}")
        # Sincronizar activo con estado
        self.activo = self.estado in ('ejecucion')
        super().save(*args, **kwargs)

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

class UsuarioProyecto(models.Model):
    """Asignación de usuarios a proyectos"""
    
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='proyectos_asignados',
        verbose_name='Usuario'
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='usuarios_asignados',
        verbose_name='Proyecto'
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Asignación'
    )
    asignado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_realizadas',
        verbose_name='Asignado por'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario_proyecto'
        unique_together = ['usuario', 'proyecto']
        verbose_name = 'Asignación Usuario-Proyecto'

    def __str__(self):
        return f"{self.usuario.nombre_completo} → {self.proyecto.nombre}"
        