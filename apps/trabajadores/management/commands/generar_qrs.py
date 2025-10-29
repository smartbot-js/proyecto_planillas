"""
Comando para regenerar códigos QR de todos los trabajadores existentes
Ejecutar: python manage.py generar_qrs
"""

from django.core.management.base import BaseCommand
from apps.trabajadores.models import Trabajador
from apps.trabajadores.utils import generar_qr_trabajador


class Command(BaseCommand):
    help = 'Genera códigos QR para todos los trabajadores que no tienen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--regenerar',
            action='store_true',
            help='Regenerar QRs incluso si ya existen',
        )
        
        parser.add_argument(
            '--solo-id',
            type=int,
            help='Generar QR solo para un trabajador específico por ID',
        )

    def handle(self, *args, **options):
        regenerar = options['regenerar']
        solo_id = options['solo_id']
        
        # Filtrar trabajadores
        if solo_id:
            trabajadores = Trabajador.objects.filter(id=solo_id, eliminado=False)
            if not trabajadores.exists():
                self.stdout.write(
                    self.style.ERROR(f'No se encontró trabajador con ID {solo_id}')
                )
                return
        else:
            if regenerar:
                trabajadores = Trabajador.objects.filter(eliminado=False)
                self.stdout.write(
                    self.style.WARNING('Regenerando QRs para TODOS los trabajadores...')
                )
            else:
                trabajadores = Trabajador.objects.filter(eliminado=False, codigo_qr='')
                self.stdout.write(
                    self.style.WARNING('Generando QRs solo para trabajadores sin código...')
                )
        
        total = trabajadores.count()
        exitosos = 0
        errores = 0
        
        self.stdout.write(f'Procesando {total} trabajadores...\n')
        
        for trabajador in trabajadores:
            try:
                generar_qr_trabajador(trabajador)
                trabajador.save(update_fields=['codigo_qr'])
                exitosos += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ QR generado para {trabajador.nombre_completo} ({trabajador.numero_cedula})')
                )
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error en {trabajador.nombre_completo}: {str(e)}')
                )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Proceso completado:'))
        self.stdout.write(f'  • Total procesados: {total}')
        self.stdout.write(self.style.SUCCESS(f'  • Exitosos: {exitosos}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  • Errores: {errores}'))
            