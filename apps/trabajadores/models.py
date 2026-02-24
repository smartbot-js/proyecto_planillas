import os
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================
# FUNCIONES PARA PATHS DE ARCHIVOS
# ============================================

def trabajador_foto_path(instance, filename):
    """Ruta para foto del trabajador"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/foto{extension}'


def trabajador_cedula_frontal_path(instance, filename):
    """Ruta para foto de cédula frontal"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/cedula_frontal{extension}'


def trabajador_cedula_posterior_path(instance, filename):
    """Ruta para foto de cédula posterior"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/cedula_posterior{extension}'


def trabajador_record_policia_path(instance, filename):
    """Ruta para record de policía"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/record_policia{extension}'


def trabajador_contrato_path(instance, filename):
    """Ruta para contrato"""
    cedula_clean = instance.numero_cedula.replace('-', '').replace(' ', '')
    extension = os.path.splitext(filename)[1]
    return f'trabajadores/{instance.id}_{cedula_clean}/contrato{extension}'


# ============================================
# MODELO TRABAJADOR
# ============================================

class Trabajador(models.Model):
    """
    Modelo para gestionar trabajadores de construcción
    Incluye información personal, laboral, documentos y auditoría
    """
    
    # ========================================
    # CHOICES
    # ========================================
    
    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        INACTIVO = 'inactivo', 'Inactivo'
        SUSPENDIDO = 'suspendido', 'Suspendido'
        RETIRADO = 'retirado', 'Retirado'
    
    class Sexo(models.TextChoices):
        MASCULINO = 'masculino', 'Masculino'
        FEMENINO = 'femenino', 'Femenino'
        OTRO = 'otro', 'Otro'
    
    class TipoSangre(models.TextChoices):
        A_POSITIVO = 'A+', 'A+'
        A_NEGATIVO = 'A-', 'A-'
        B_POSITIVO = 'B+', 'B+'
        B_NEGATIVO = 'B-', 'B-'
        AB_POSITIVO = 'AB+', 'AB+'
        AB_NEGATIVO = 'AB-', 'AB-'
        O_POSITIVO = 'O+', 'O+'
        O_NEGATIVO = 'O-', 'O-'
    
    # ========================================
    # INFORMACIÓN PERSONAL
    # ========================================
    
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    
    apellido = models.CharField(
        max_length=100,
        verbose_name='Apellido'
    )
    
    numero_cedula = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Número de Cédula',
        help_text='Documento de identidad único'
    )
    
    fecha_nacimiento = models.DateField(
        verbose_name='Fecha de Nacimiento',
        null=True,
        blank=True
    )
    
    sexo = models.CharField(
        max_length=20,
        choices=Sexo.choices,
        default=Sexo.MASCULINO,
        verbose_name='Sexo'
    )
    
    tipo_sangre = models.CharField(
        max_length=5,
        choices=TipoSangre.choices,
        blank=True,
        verbose_name='Tipo de Sangre'
    )
    
    # ========================================
    # UBICACIÓN
    # ========================================
    
    departamento = models.CharField(
        max_length=100,
        verbose_name='Departamento',
        blank=True
    )
    
    municipio = models.CharField(
        max_length=100,
        verbose_name='Municipio',
        blank=True
    )
    
    direccion = models.TextField(
        verbose_name='Dirección',
        blank=True
    )
    
    # ========================================
    # CONTACTO
    # ========================================
    
    telefono = models.CharField(
        max_length=20,
        verbose_name='Teléfono',
        blank=True
    )
    
    email = models.EmailField(
        verbose_name='Correo Electrónico',
        blank=True,
        null=True
    )
    
    contacto_emergencia = models.CharField(
        max_length=200,
        verbose_name='Contacto de Emergencia',
        blank=True,
        help_text='Nombre y teléfono de contacto de emergencia'
    )
    
    # ========================================
    # INFORMACIÓN LABORAL
    # ========================================
    
    proyecto_asignado = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores',
        verbose_name='Proyecto Asignado'
    )
    
    puesto_laboral = models.CharField(
        max_length=100,
        verbose_name='Puesto Laboral'
    )
    
    area_cargo = models.CharField(
        max_length=100,
        verbose_name='Área/Cargo',
        blank=True
    )
    
    fecha_ingreso = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Ingreso'
    )
    
    fecha_salida = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Salida'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        verbose_name='Estado'
    )
    
    # ========================================
    # SALARIOS Y PAGOS
    # ========================================
    
    salario_normal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Salario Normal (por hora)',
        help_text='Tarifa por hora normal'
    )
    
    tarifa_hora_extra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Tarifa Hora Extra',
        help_text='Tarifa por día o por hora extra'
    )
    
    salario_festivo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Salario Festivo',
        blank=True
    )
    
    salario_nocturno = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Salario Nocturno',
        blank=True
    )
    
    # ========================================
    # SEGURIDAD SOCIAL
    # ========================================
    
    numero_seguro_social = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Número de Seguro Social'
    )
    
    asegurado = models.BooleanField(
        default=False,
        verbose_name='Asegurado'
    )
    
    record_policia = models.BooleanField(
        default=False,
        verbose_name='Record de Policía Entregado'
    )
    
    # ========================================
    # DOCUMENTOS
    # ========================================
    
    foto = models.ImageField(
        upload_to=trabajador_foto_path,
        blank=True,
        null=True,
        verbose_name='Foto del Trabajador'
    )
    
    foto_cedula_frontal = models.ImageField(
        upload_to=trabajador_cedula_frontal_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Frontal)'
    )
    
    foto_cedula_posterior = models.ImageField(
        upload_to=trabajador_cedula_posterior_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Posterior)'
    )
    
    # Mantener compatibilidad con código anterior
    foto_cedula = models.ImageField(
        upload_to=trabajador_cedula_frontal_path,
        blank=True,
        null=True,
        verbose_name='Foto de Cédula (Única)'
    )
    
    record_policia_doc = models.FileField(
        upload_to=trabajador_record_policia_path,
        blank=True,
        null=True,
        verbose_name='Record de Policía (Documento)'
    )
    
    archivo_contrato = models.FileField(
        upload_to=trabajador_contrato_path,
        blank=True,
        null=True,
        verbose_name='Archivo de Contrato'
    )
    
    codigo_qr = models.ImageField(
        upload_to='trabajadores/qr/',
        blank=True,
        null=True,
        verbose_name='Código QR',
        help_text='Código QR generado automáticamente para registro de asistencias'
    )
    # ========================================
    # NOTAS Y OBSERVACIONES
    # ========================================
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Observaciones adicionales sobre el trabajador'
    )
    
    # ========================================
    # AUDITORÍA
    # ========================================
    
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en'
    )
    
    modificado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Modificado en'
    )
    
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores_creados',
        verbose_name='Creado por'
    )
    
    modificado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trabajadores_modificados',
        verbose_name='Modificado por'
    )
    
    eliminado = models.BooleanField(
        default=False,
        verbose_name='Eliminado'
    )
    
    # ========================================
    # META Y MÉTODOS
    # ========================================
    
    class Meta:
        db_table = 'trabajadores'
        verbose_name = 'Trabajador'
        verbose_name_plural = 'Trabajadores'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['numero_cedula']),
            models.Index(fields=['estado']),
            models.Index(fields=['proyecto_asignado']),
            models.Index(fields=['eliminado']),
        ]
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.numero_cedula}"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del trabajador"""
        return f"{self.nombre} {self.apellido}".strip()
    
    @property
    def edad(self):
        """Calcula la edad del trabajador"""
        if self.fecha_nacimiento:
            today = timezone.now().date()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None

    @property
    def foto_cedula_es_imagen(self):
        """
        Verifica si el archivo 'foto_cedula' es una imagen basándose en la extensión.
        """
        if not self.foto_cedula:
            return False
        try:
            filename = self.foto_cedula.name
            _name, extension = os.path.splitext(filename)
            return extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        except Exception:
            return False

    @property
    def record_policia_es_imagen(self):
        """
        Verifica si el 'record_policia_doc' es una imagen.
        """
        if not self.record_policia_doc:
            return False
        try:
            filename = self.record_policia_doc.name
            _name, extension = os.path.splitext(filename)
            return extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        except Exception:
            return False

    @property
    def tiempo_servicio(self):
        """Calcula el tiempo de servicio en días"""
        if self.fecha_ingreso:
            fecha_fin = self.fecha_salida if self.fecha_salida else timezone.now().date()
            return (fecha_fin - self.fecha_ingreso).days
        return 0
    
    @property
    def esta_activo(self):
        """Verifica si el trabajador está activo"""
        return self.estado == self.Estado.ACTIVO and not self.eliminado
    
    @property
    def tiene_documentos_completos(self):
        """Verifica si el trabajador tiene todos los documentos"""
        return bool(
            self.foto and
            (self.foto_cedula or (self.foto_cedula_frontal and self.foto_cedula_posterior)) and
            (self.record_policia_doc if self.record_policia else True)
        )
    
    def soft_delete(self):
        """Realiza un borrado lógico del trabajador"""
        self.eliminado = True
        self.estado = self.Estado.INACTIVO
        self.save()
    
    def restore(self):
        """Restaura un trabajador eliminado"""
        self.eliminado = False
        self.estado = self.Estado.ACTIVO
        self.save()
    
    def asignar_proyecto(self, proyecto):
        """Asigna el trabajador a un proyecto"""
        self.proyecto_asignado = proyecto
        self.save()
    
    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado del trabajador"""
        if nuevo_estado in dict(self.Estado.choices):
            self.estado = nuevo_estado
            if nuevo_estado == self.Estado.RETIRADO and not self.fecha_salida:
                self.fecha_salida = timezone.now().date()
            self.save()
            return True
        return False
    
    def get_salario_diario(self):
        """Calcula el salario diario estimado (8 horas)"""
        return self.salario_normal * 8
    
    def get_salario_mensual_estimado(self):
        """Calcula el salario mensual estimado (22 días laborables)"""
        return self.get_salario_diario() * 22


# ============================================
# MODELO HISTORIAL DE PROYECTOS
# ============================================

class HistorialProyecto(models.Model):
    """
    Modelo para registrar el historial de asignaciones de trabajadores a proyectos
    """
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.CASCADE,
        related_name='historial_proyectos',
        verbose_name='Trabajador'
    )
    
    proyecto = models.ForeignKey(
        'proyectos.Proyecto',
        on_delete=models.CASCADE,
        related_name='historial_trabajadores',
        verbose_name='Proyecto'
    )
    
    fecha_asignacion = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de Asignación'
    )
    
    fecha_salida = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Salida'
    )
    
    motivo = models.TextField(
        blank=True,
        verbose_name='Motivo',
        help_text='Motivo de la asignación o traslado'
    )
    
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en'
    )
    
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Creado por'
    )
    
    class Meta:
        db_table = 'trabajadores_historial_proyectos'
        verbose_name = 'Historial de Proyecto'
        verbose_name_plural = 'Historiales de Proyectos'
        ordering = ['-fecha_asignacion']
    
    def __str__(self):
        return f"{self.trabajador.nombre_completo} - {self.proyecto.nombre}"


# ============================================
# MODELO DOCUMENTOS ADICIONALES
# ============================================

class DocumentoTrabajador(models.Model):
    """
    Modelo para almacenar documentos adicionales del trabajador
    """
    
    class TipoDocumento(models.TextChoices):
        CONTRATO = 'contrato', 'Contrato'
        CERTIFICADO = 'certificado', 'Certificado'
        TITULO = 'titulo', 'Título'
        LICENCIA = 'licencia', 'Licencia'
        OTRO = 'otro', 'Otro'
    
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.CASCADE,
        related_name='documentos_adicionales',
        verbose_name='Trabajador'
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.OTRO,
        verbose_name='Tipo de Documento'
    )
    
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre del Documento'
    )
    
    archivo = models.FileField(
        upload_to='trabajadores/documentos/',
        verbose_name='Archivo'
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Emisión'
    )
    
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Vencimiento'
    )
    
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en'
    )
    
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Creado por'
    )
    
    class Meta:
        db_table = 'trabajadores_documentos'
        verbose_name = 'Documento del Trabajador'
        verbose_name_plural = 'Documentos de Trabajadores'
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"{self.nombre} - {self.trabajador.nombre_completo}"
    
    @property
    def esta_vencido(self):
        """Verifica si el documento está vencido"""
        if self.fecha_vencimiento:
            return self.fecha_vencimiento < timezone.now().date()
        return False
    