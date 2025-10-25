"""
Configuración de la aplicación de proyectos
"""

from django.apps import AppConfig


class ProyectosConfig(AppConfig):
    """Configuración de la app proyectos"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.proyectos'
    verbose_name = 'Gestión de Proyectos'
    
    def ready(self):
        """
        Método que se ejecuta cuando la aplicación está lista
        """
        pass