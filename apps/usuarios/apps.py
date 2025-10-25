"""
Configuración de la aplicación de usuarios
"""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Configuración de la app usuarios"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'
    verbose_name = 'Gestión de Usuarios'

    def ready(self):
        """
        Método que se ejecuta cuando la aplicación está lista
        Aquí se pueden importar signals u otras configuraciones
        """
        pass