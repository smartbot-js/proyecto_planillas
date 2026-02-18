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
        #extra_fields.setdefault('rol', 'administrador')

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

    # Sistema de roles y aprobación
    rol = models.ForeignKey(
        'admin_panel.Rol',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name=_('Rol')
    )

    cuenta_aprobada = models.BooleanField(
        _('Cuenta Aprobada'),
        default=False
    )

    aprobada_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cuentas_que_aprobo',
        verbose_name=_('Aprobada por')
    )

    fecha_aprobacion = models.DateTimeField(
        _('Fecha de Aprobación'),
        null=True,
        blank=True
    )
    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['-fecha_creacion']
        db_table = 'usuarios'

    def __str__(self):
        rol_nombre = self.rol.nombre if self.rol else 'Sin rol'
        return f"{self.email} - {rol_nombre}"

    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        return self.nombre_completo

    def get_short_name(self):
        """Retorna el nombre corto del usuario"""
        return self.nombre_completo.split()[0] if self.nombre_completo else self.email

    def es_administrador(self):
        if self.is_superuser:
            return True
        if self.rol:
            return self.rol.codigo in ['admin', 'gerente_general']
        return False

    def es_supervisor(self):
        if self.is_superuser:
            return True
        if self.rol:
            return self.rol.codigo in ['gerente_proyecto', 'residente', 'admin', 'gerente_general']
        return False

    def es_trabajador(self):
        if self.rol:
            return self.rol.codigo == 'asistencia'
        return False

    def puede_validar_asistencias(self):
        return self.es_administrador() or self.es_supervisor()

    def puede_gestionar_proyectos(self):
        return self.es_administrador()

    def puede_ver_todos_reportes(self):
        return self.es_administrador()

    def tiene_permiso(self, modulo, accion):
        if self.is_superuser:
            return True
        if not self.rol:
            return False
        permisos = self.rol.permisos or {}
        return permisos.get(modulo, {}).get(accion, False)

    def get_proyectos_permitidos(self):
        """Retorna queryset de proyectos que puede ver según su rol"""
        from apps.proyectos.models import Proyecto, UsuarioProyecto
        
        # Admin, Gerente General, Contador → todos
        if self.is_superuser:
            return Proyecto.objects.filter(eliminado=False)
        
        if self.rol and self.rol.codigo in ['admin', 'gerente_general', 'contador']:
            return Proyecto.objects.filter(eliminado=False)
        
        # Gerente de Proyecto → proyectos asignados (varios)
        if self.rol and self.rol.codigo == 'gerente_proyecto':
            ids = UsuarioProyecto.objects.filter(
                usuario=self, activo=True
            ).values_list('proyecto_id', flat=True)
            return Proyecto.objects.filter(id__in=ids, eliminado=False)
        
        # Residente / Maestro de Obra → solo 1 proyecto
        if self.rol and self.rol.codigo == 'residente':
            ids = UsuarioProyecto.objects.filter(
                usuario=self, activo=True
            ).values_list('proyecto_id', flat=True)
            return Proyecto.objects.filter(id__in=ids, eliminado=False)
        
        # Sin rol → ningún proyecto
        return Proyecto.objects.none()

    def puede_ver_proyecto(self, proyecto):
        """Verifica si puede ver un proyecto específico"""
        if self.is_superuser:
            return True
        if self.rol and self.rol.codigo in ['admin', 'gerente_general', 'contador']:
            return True
        return self.get_proyectos_permitidos().filter(pk=proyecto.pk).exists()