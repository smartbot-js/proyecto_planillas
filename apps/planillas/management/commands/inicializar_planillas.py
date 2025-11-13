"""
Comando para inicializar el módulo de planillas con datos iniciales
apps/planillas/management/commands/inicializar_planillas.py

Uso:
    python manage.py inicializar_planillas
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.planillas.models import TipoCambio, DiaFeriado
from apps.proyectos.models import Proyecto
from decimal import Decimal


class Command(BaseCommand):
    help = 'Inicializa el módulo de planillas con datos iniciales (tipo cambio, feriados, proyecto admin)'
    
    # ✅ Definir verbosity como atributo de clase
    verbosity = 1

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar recarga de datos incluso si ya existen'
        )

    def handle(self, *args, **options):
        forzar = options.get('forzar', False)
        self.verbosity = options.get('verbosity', 1)
        
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.WARNING('🚀 INICIALIZACIÓN DEL MÓDULO DE PLANILLAS'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        try:
            with transaction.atomic():
                
                # ============================================================
                # 1. TIPO DE CAMBIO
                # ============================================================
                self.stdout.write('📊 Configurando tipo de cambio...')
                
                tipo_cambio_actual = TipoCambio.objects.filter(activo=True).first()
                
                if tipo_cambio_actual:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠️  Ya existe un tipo de cambio activo: C$ {tipo_cambio_actual.valor}'
                        )
                    )
                    if not forzar:
                        self.stdout.write('     (Usa --forzar para actualizar)')
                else:
                    tipo_cambio = TipoCambio.objects.create(
                        valor=Decimal('36.6000'),
                        activo=True,
                        fecha=timezone.now().date()
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ Tipo de cambio creado: C$ {tipo_cambio.valor}'
                        )
                    )
                
                # ============================================================
                # 2. DÍAS FERIADOS
                # ============================================================
                self.stdout.write('\n📅 Sincronizando días feriados de Nicaragua...')
                
                # Verificar si ya existen feriados
                anio_actual = timezone.now().year
                feriados_existentes = DiaFeriado.objects.filter(
                    fecha__year=anio_actual,
                    tipo='nacional'
                ).count()
                
                if feriados_existentes > 0 and not forzar:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠️  Ya existen {feriados_existentes} feriados para {anio_actual}'
                        )
                    )
                    self.stdout.write('     (Usa --forzar para recargar)')
                else:
                    # Verificar que la librería holidays esté instalada
                    try:
                        import holidays
                        
                        # Cargar feriados de Nicaragua
                        total_cargados = DiaFeriado.cargar_feriados_pais(pais='NI')
                        
                        if total_cargados > 0:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✅ {total_cargados} feriados nuevos cargados'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    '  ℹ️  Feriados ya estaban actualizados'
                                )
                            )
                        
                        # Mostrar resumen
                        total_feriados = DiaFeriado.objects.filter(
                            fecha__year__in=[anio_actual, anio_actual + 1],
                            tipo='nacional',
                            activo=True
                        ).count()
                        
                        self.stdout.write(
                            f'  📌 Total de feriados disponibles: {total_feriados}'
                        )
                        
                    except ImportError:
                        self.stdout.write(
                            self.style.ERROR(
                                '  ❌ La librería "holidays" no está instalada.'
                            )
                        )
                        self.stdout.write(
                            self.style.WARNING(
                                '     Instálala con: pip install holidays'
                            )
                        )
                        self.stdout.write('')
                        self.stdout.write('     Cargando feriados manualmente...')
                        
                        # Cargar feriados manualmente como fallback
                        total_manual = self._cargar_feriados_manual(anio_actual)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ {total_manual} feriados cargados manualmente'
                            )
                        )
                
                # ============================================================
                # 3. PROYECTO "ADMINISTRACIÓN GENERAL"
                # ============================================================
                self.stdout.write('\n🏢 Verificando proyecto administrativo...')
                
                # ✅ CORRECCIÓN: Usar campos correctos del modelo Proyecto
                proyecto_admin, created = Proyecto.objects.get_or_create(
                    nombre='Administración General',
                    defaults={
                        'descripcion': 'Proyecto virtual para agrupar personal administrativo (secretarias, contadores, gerencia, etc.)',
                        'ubicacion': 'Oficina Central',  # ✅ Cambio: direccion → ubicacion
                        'estado': 'ejecucion',
                        'fecha_inicio': timezone.now().date(),
                        'supervisor_id': 1,  # ✅ Asume que el superuser tiene ID 1
                        'tipo_proyecto': 'comercial',  # ✅ Campo requerido
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            '  ✅ Proyecto "Administración General" creado exitosamente'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            '  ℹ️  Proyecto "Administración General" ya existe'
                        )
                    )
                
                # ============================================================
                # 4. RESUMEN FINAL
                # ============================================================
                self.stdout.write('\n' + '=' * 70)
                self.stdout.write(self.style.SUCCESS('✅ INICIALIZACIÓN COMPLETADA'))
                self.stdout.write('=' * 70)
                self.stdout.write('')
                
                # Obtener datos actuales
                tipo_cambio_final = TipoCambio.get_actual()
                total_feriados_final = DiaFeriado.objects.filter(activo=True).count()
                total_proyectos = Proyecto.objects.filter(eliminado=False).count()
                
                self.stdout.write('📊 RESUMEN:')
                self.stdout.write(f'  • Tipo de cambio activo: C$ {tipo_cambio_final.valor}')
                self.stdout.write(f'  • Días feriados cargados: {total_feriados_final}')
                self.stdout.write(f'  • Proyectos disponibles: {total_proyectos}')
                self.stdout.write('')
                
                self.stdout.write('🎯 PRÓXIMOS PASOS:')
                self.stdout.write('  1. Accede al sistema web')
                self.stdout.write('  2. Ve a la sección de Planillas')
                self.stdout.write('  3. Genera tu primera planilla')
                self.stdout.write('')
                
                self.stdout.write('💡 COMANDOS ÚTILES:')
                self.stdout.write('  • Sincronizar feriados: python manage.py sincronizar_feriados')
                self.stdout.write('  • Actualizar tipo de cambio: desde el panel de Planillas')
                self.stdout.write('')
                
                self.stdout.write('=' * 70)
                self.stdout.write('')
                
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('❌ ERROR DURANTE LA INICIALIZACIÓN'))
            self.stdout.write(self.style.ERROR(f'   {str(e)}'))
            self.stdout.write('')
            
            if self.verbosity >= 2:
                import traceback
                self.stdout.write(traceback.format_exc())
    
    def _cargar_feriados_manual(self, anio):
        """
        Carga feriados manualmente como fallback si la librería holidays no está disponible
        """
        from datetime import datetime
        
        feriados_nicaragua = [
            ('01-01', 'Año Nuevo'),
            ('04-17', 'Jueves Santo'),  # 2025
            ('04-18', 'Viernes Santo'),  # 2025
            ('05-01', 'Día Internacional del Trabajo'),
            ('05-30', 'Día de la Madre'),
            ('07-19', 'Día de la Revolución'),
            ('09-14', 'Batalla de San Jacinto'),
            ('09-15', 'Día de la Independencia'),
            ('12-08', 'Concepción de María'),
            ('12-25', 'Navidad'),
        ]
        
        contador = 0
        
        for fecha_str, descripcion in feriados_nicaragua:
            try:
                fecha = datetime.strptime(f'{anio}-{fecha_str}', '%Y-%m-%d').date()
                
                obj, created = DiaFeriado.objects.get_or_create(
                    fecha=fecha,
                    tipo='nacional',
                    proyecto=None,
                    defaults={
                        'descripcion': descripcion,
                        'activo': True
                    }
                )
                
                if created:
                    contador += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️  No se pudo crear feriado {descripcion}: {str(e)}'
                    )
                )
        
        # Cargar también para el año siguiente
        anio_siguiente = anio + 1
        for fecha_str, descripcion in feriados_nicaragua:
            try:
                fecha = datetime.strptime(f'{anio_siguiente}-{fecha_str}', '%Y-%m-%d').date()
                
                obj, created = DiaFeriado.objects.get_or_create(
                    fecha=fecha,
                    tipo='nacional',
                    proyecto=None,
                    defaults={
                        'descripcion': descripcion,
                        'activo': True
                    }
                )
                
                if created:
                    contador += 1
                    
            except Exception:
                pass
        
        return contador