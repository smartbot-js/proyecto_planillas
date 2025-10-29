from django.apps import AppConfig


class TrabajadoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.trabajadores'
    verbose_name = 'Trabajadores'
    
    def ready(self):
        """Importar signals cuando la app esté lista"""
        import apps.trabajadores.signals