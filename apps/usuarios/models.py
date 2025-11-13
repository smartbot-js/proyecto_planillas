"""
Modelos de la aplicación de usuarios
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UsuarioManager(BaseUserManager):
    """
    Manager personalizado para el modelo Usuario
    Maneja la creación de usuarios y superusuarios
    """

    def create_user(self, email, nombre_completo, password=None, **extra_fields):
        """
        Crea y guarda un Usuario con el email y password proporcionados
        """
        if not email:
            raise ValueError(_('El email es obligatorio'))
        
        if not nombre_completo:
            raise ValueError(_('El nombre completo es obligatorio'))

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            nombre_completo=nombre_completo,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre_completo, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el email y password proporcionados
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('rol', 'administrador')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('El superusuario debe tener is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('El superusuario debe tener is_superuser=True.'))

        return self.create_user(email, nombre_completo, password, **extra_fields)


class Usuario(AbstractUser):
    """
    Modelo de Usuario personalizado para el Sistema de Planillas
    
    Atributos:
        email: Email único para autenticación
        nombre_completo: Nombre completo del usuario
        rol: Rol del usuario en el sistema (administrador, supervisor, trabajador)
        activo: Estado de la cuenta del usuario
        fecha_creacion: Fecha de creación del usuario
        fecha_actualizacion: Fecha de última actualización
    """

    class Rol(models.TextChoices):
        """Roles disponibles en el sistema"""
        ADMINISTRADOR = 'administrador', _('Administrador')
        GERENTE = 'gerente', _('Gerente')
        CONTADOR = 'contador', _('Contador')
        RESIDENTE = 'residente', _('Residente de Obra')
        SUPERVISOR = 'supervisor', _('Supervisor')
        TRABAJADOR = 'trabajador', _('Trabajador')
        
    # Eliminamos el campo username, usaremos email
    username = None
    first_name = None
    last_name = None

    # Campos personalizados
    email = models.EmailField(
        _('Correo Electrónico'),
        unique=True,
        error_messages={
            'unique': _('Ya existe un usuario con este correo electrónico.'),
        },
        help_text=_('Correo electrónico para autenticación')
    )

    nombre_completo = models.CharField(
        _('Nombre Completo'),
        max_length=255,
        help_text=_('Nombre completo del usuario')
    )

    rol = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Rol.choices,
        default=Rol.TRABAJADOR,
        help_text=_('Rol del usuario en el sistema')
    )

    activo = models.BooleanField(
        _('Activo'),
        default=True,
        help_text=_('Indica si el usuario puede acceder al sistema')
    )

    # Campos de auditoría
    fecha_creacion = models.DateTimeField(
        _('Fecha de Creación'),
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        _('Fecha de Actualización'),
        auto_now=True
    )

    # Solución al conflicto con auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('grupos'),
        blank=True,
        help_text=_('Los grupos a los que pertenece este usuario.'),
        related_name='usuario_set',
        related_query_name='usuario',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('permisos de usuario'),
        blank=True,
        help_text=_('Permisos específicos para este usuario.'),
        related_name='usuario_set',
        related_query_name='usuario',
    )

    # Configuración del modelo
    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['-fecha_creacion']
        db_table = 'usuarios'

    def __str__(self):
        """Representación en string del usuario"""
        return f"{self.email} - {self.get_rol_display()}"

    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        return self.nombre_completo

    def get_short_name(self):
        """Retorna el nombre corto del usuario"""
        return self.nombre_completo.split()[0] if self.nombre_completo else self.email

    def es_administrador(self):
        """Verifica si el usuario es administrador"""
        return self.rol == self.Rol.ADMINISTRADOR

    def es_supervisor(self):
        """Verifica si el usuario es supervisor"""
        return self.rol == self.Rol.SUPERVISOR

    def es_trabajador(self):
        """Verifica si el usuario es trabajador"""
        return self.rol == self.Rol.TRABAJADOR

    def puede_validar_asistencias(self):
        """Verifica si el usuario puede validar asistencias"""
        return self.rol in [self.Rol.ADMINISTRADOR, self.Rol.SUPERVISOR]

    def puede_gestionar_proyectos(self):
        """Verifica si el usuario puede gestionar proyectos"""
        return self.rol == self.Rol.ADMINISTRADOR

    def puede_ver_todos_reportes(self):
        """Verifica si el usuario puede ver todos los reportes"""
        return self.rol == self.Rol.ADMINISTRADOR
    