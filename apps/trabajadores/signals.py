"""
Signals para el módulo de trabajadores
Automatización de tareas al crear/modificar trabajadores
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Trabajador
from .utils import generar_qr_trabajador


@receiver(post_save, sender=Trabajador)
def auto_generar_qr(sender, instance, created, **kwargs):
    """
    Genera automáticamente el código QR cuando se crea un trabajador
    """
    # Solo generar si es nuevo y no tiene QR ya
    if created and not instance.codigo_qr:
        try:
            generar_qr_trabajador(instance)
            instance.save(update_fields=['codigo_qr'])
        except Exception as e:
            # Si falla, no detener la creación del trabajador
            print(f"Error al generar QR para {instance.numero_cedula}: {str(e)}")
            