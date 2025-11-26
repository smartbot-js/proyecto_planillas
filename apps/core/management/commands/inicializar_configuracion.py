"""
Comando para inicializar la configuración del sistema
apps/core/management/commands/inicializar_configuracion.py

Uso:
    python manage.py inicializar_configuracion
"""
from django.core.management.base import BaseCommand
from apps.core.models import ConfiguracionSistema
from decimal import Decimal


class Command(BaseCommand):
    help = 'Inicializa la configuración del sistema con valores por defecto'
    
    def handle(self, *args, **options):
        self.stdout.write('Inicializando configuración del sistema...')
        
        # Verificar si ya existe
        if ConfiguracionSistema.objects.exists():
            config = ConfiguracionSistema.get_configuracion()
            self.stdout.write(self.style.WARNING(
                '⚠️  La configuración ya existe.'
            ))
        else:
            # Crear configuración
            config = ConfiguracionSistema.objects.create()
            self.stdout.write(self.style.SUCCESS(
                '✅ Configuración creada correctamente'
            ))
        
        self.stdout.write(f'   - Tipo de Cambio: C$ {config.tipo_cambio_actual}')
        self.stdout.write(f'   - Nombre Empresa: {config.nombre_empresa}')
        self.stdout.write(f'   - Última actualización: {config.actualizado_en}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Inicialización completada!'))