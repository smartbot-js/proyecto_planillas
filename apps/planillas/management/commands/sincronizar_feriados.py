"""
Comando para sincronizar días feriados desde la librería holidays
apps/planillas/management/commands/sincronizar_feriados.py
"""

from django.core.management.base import BaseCommand
from apps.planillas.models import DiaFeriado
from datetime import datetime


class Command(BaseCommand):
    help = 'Sincroniza días feriados nacionales desde la librería holidays'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pais',
            type=str,
            default='NI',
            help='Código ISO del país (NI=Nicaragua, CR=Costa Rica, etc.)'
        )
        parser.add_argument(
            '--anio',
            type=int,
            help='Año específico a cargar. Si no se especifica, carga año actual y siguiente'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar recarga incluso si ya existen feriados'
        )

    def handle(self, *args, **options):
        pais = options['pais']
        anio = options.get('anio')
        forzar = options.get('forzar', False)
        
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.WARNING('SINCRONIZACIÓN DE DÍAS FERIADOS'))
        self.stdout.write('=' * 70)
        
        # Verificar si la librería está instalada
        try:
            import holidays
            self.stdout.write(self.style.SUCCESS('✅ Librería holidays encontrada'))
        except ImportError:
            self.stdout.write(self.style.ERROR(
                '❌ Error: La librería "holidays" no está instalada.\n'
                '   Instálala con: pip install holidays'
            ))
            return
        
        # Mostrar países disponibles
        paises_disponibles = {
            'NI': 'Nicaragua',
            'CR': 'Costa Rica',
            'GT': 'Guatemala',
            'HN': 'Honduras',
            'SV': 'El Salvador',
            'PA': 'Panamá',
            'MX': 'México',
            'US': 'Estados Unidos',
        }
        
        nombre_pais = paises_disponibles.get(pais, pais)
        self.stdout.write(f'\n📍 País: {nombre_pais} ({pais})')
        
        # Determinar años a cargar
        if anio:
            anios = [anio]
            self.stdout.write(f'📅 Año: {anio}')
        else:
            anio_actual = datetime.now().year
            anios = [anio_actual, anio_actual + 1]
            self.stdout.write(f'📅 Años: {anio_actual} y {anio_actual + 1}')
        
        # Verificar si ya existen feriados
        if not forzar:
            for anio_check in anios:
                existe = DiaFeriado.objects.filter(
                    fecha__year=anio_check,
                    tipo='nacional'
                ).exists()
                if existe:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\n⚠️  Ya existen feriados para el año {anio_check}'
                        )
                    )
                    confirmar = input('¿Deseas continuar y actualizar? (s/n): ')
                    if confirmar.lower() not in ['s', 'si', 'yes', 'y']:
                        self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                        return
        
        # Cargar feriados
        self.stdout.write('\n🔄 Cargando feriados...\n')
        
        try:
            if anio:
                total = DiaFeriado.cargar_feriados_pais(pais=pais, anio=anio)
            else:
                total = DiaFeriado.cargar_feriados_pais(pais=pais)
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ {total} feriados nuevos cargados exitosamente'))
            
            # Mostrar resumen
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS('RESUMEN DE FERIADOS CARGADOS'))
            self.stdout.write('=' * 70 + '\n')
            
            for anio_resumen in anios:
                feriados = DiaFeriado.objects.filter(
                    fecha__year=anio_resumen,
                    tipo='nacional',
                    activo=True
                ).order_by('fecha')
                
                self.stdout.write(self.style.WARNING(f'\n📅 AÑO {anio_resumen} ({feriados.count()} feriados):'))
                self.stdout.write('-' * 70)
                
                for feriado in feriados:
                    fecha_str = feriado.fecha.strftime('%d/%m/%Y - %A')
                    self.stdout.write(f'  • {fecha_str}: {feriado.descripcion}')
            
            self.stdout.write('\n' + '=' * 70)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error al cargar feriados: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())