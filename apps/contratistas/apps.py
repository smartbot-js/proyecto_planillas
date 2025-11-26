"""
Configuración de la aplicación Contratistas
"""
from django.apps import AppConfig


class ContratistasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contratistas'
    verbose_name = 'Contratistas'
    