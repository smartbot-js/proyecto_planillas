from django.db import models
from apps.usuarios.models import Usuario

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    codigo = models.SlugField(max_length=30, unique=True, verbose_name='Código')
    
    es_sistema = models.BooleanField(default=False, verbose_name='Es rol del sistema')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    
    permisos = models.JSONField(default=dict, verbose_name='Permisos')
    
    alcance_proyectos = models.CharField(
        max_length=20,
        choices=[
            ('todos', 'Todos los proyectos'),
            ('asignados', 'Solo proyectos asignados'),
            ('propio', 'Solo proyecto propio'),
            ('ninguno', 'Sin acceso a proyectos')
        ],
        default='asignados',
        verbose_name='Alcance de proyectos'
    )
    
    solo_app_movil = models.BooleanField(default=False, verbose_name='Solo app móvil')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='roles_creados',
        verbose_name='Creado por'
    )
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']
        db_table = 'roles'
    
    def __str__(self):
        return self.nombre
        