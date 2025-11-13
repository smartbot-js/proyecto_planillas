# ============================================================
# COMANDO PARA RECALCULAR HORAS INCORRECTAS
# apps/asistencias/management/commands/recalcular_horas.py
# ============================================================

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.asistencias.models import Asistencia
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalcula las horas de todas las asistencias con datos incorrectos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Recalcular TODAS las asistencias (no solo las incorrectas)',
        )
        parser.add_argument(
            '--fecha-desde',
            type=str,
            help='Fecha desde (formato: YYYY-MM-DD)',
        )
        parser.add_argument(
            '--fecha-hasta',
            type=str,
            help='Fecha hasta (formato: YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando recálculo de horas...'))
        
        # Obtener todas las asistencias
        asistencias = Asistencia.objects.filter(eliminado=False)
        
        # Filtrar por fechas si se especifican
        if options['fecha_desde']:
            asistencias = asistencias.filter(fecha__gte=options['fecha_desde'])
            self.stdout.write(f"Filtrando desde: {options['fecha_desde']}")
        
        if options['fecha_hasta']:
            asistencias = asistencias.filter(fecha__lte=options['fecha_hasta'])
            self.stdout.write(f"Filtrando hasta: {options['fecha_hasta']}")
        
        # Si no se especifica --todos, solo recalcular las problemáticas
        if not options['todos']:
            # Filtrar solo asistencias con horas > 24 o con entrada/salida iguales y horas > 0
            self.stdout.write(self.style.WARNING('Filtrando solo asistencias problemáticas...'))
            asistencias_a_corregir = []
            
            for asistencia in asistencias:
                if asistencia.hora_entrada and asistencia.hora_salida:
                    # Caso 1: Horas totales > 24h (definitivamente incorrecto)
                    if asistencia.horas_totales > 24:
                        asistencias_a_corregir.append(asistencia)
                    # Caso 2: Entrada == Salida pero tiene horas > 0
                    elif asistencia.hora_entrada == asistencia.hora_salida and asistencia.horas_totales > 0:
                        asistencias_a_corregir.append(asistencia)
                    # Caso 3: Horas extras > 16h (sospechoso)
                    elif asistencia.horas_extras > 16:
                        asistencias_a_corregir.append(asistencia)
            
            asistencias = asistencias_a_corregir
            self.stdout.write(f"Encontradas {len(asistencias)} asistencias problemáticas")
        else:
            self.stdout.write(f"Total de asistencias a recalcular: {asistencias.count()}")
        
        if not asistencias:
            self.stdout.write(self.style.SUCCESS('✅ No hay asistencias que corregir'))
            return
        
        # Mostrar resumen de lo que se va a corregir
        self.stdout.write(self.style.WARNING('\n📋 RESUMEN DE ASISTENCIAS A CORREGIR:'))
        self.stdout.write('─' * 100)
        self.stdout.write(f"{'Fecha':<12} {'Trabajador':<25} {'Entrada':<8} {'Salida':<8} {'Horas Actual':<12} {'Estado'}")
        self.stdout.write('─' * 100)
        
        for asistencia in asistencias[:10]:  # Mostrar solo las primeras 10
            trabajador = asistencia.trabajador.nombre_completo[:24]
            entrada = asistencia.hora_entrada.strftime('%H:%M') if asistencia.hora_entrada else 'N/A'
            salida = asistencia.hora_salida.strftime('%H:%M') if asistencia.hora_salida else 'N/A'
            horas = f"{asistencia.horas_totales}h"
            
            self.stdout.write(
                f"{asistencia.fecha} {trabajador:<25} {entrada:<8} {salida:<8} {horas:<12} ❌"
            )
        
        if len(asistencias) > 10:
            self.stdout.write(f"... y {len(asistencias) - 10} más")
        
        self.stdout.write('─' * 100)
        
        # Confirmar antes de proceder
        if not options.get('verbosity') or options['verbosity'] > 0:
            confirmar = input('\n¿Deseas continuar con el recálculo? (si/no): ')
            if confirmar.lower() not in ['si', 's', 'yes', 'y']:
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return
        
        # Recalcular con transacción
        corregidas = 0
        errores = 0
        
        self.stdout.write(self.style.WARNING('\n🔄 Recalculando...'))
        
        with transaction.atomic():
            for asistencia in asistencias:
                try:
                    # Guardar valores anteriores para log
                    horas_anteriores = float(asistencia.horas_totales)
                    
                    # Recalcular (llama al método calcular_horas del modelo)
                    asistencia.calcular_horas()
                    asistencia.save()
                    
                    horas_nuevas = float(asistencia.horas_totales)
                    
                    # Solo contar como corregida si cambió
                    if abs(horas_anteriores - horas_nuevas) > 0.01:
                        corregidas += 1
                        
                        if options['verbosity'] > 1:
                            self.stdout.write(
                                f"✅ {asistencia.trabajador.nombre_completo} - {asistencia.fecha}: "
                                f"{horas_anteriores:.2f}h → {horas_nuevas:.2f}h"
                            )
                
                except Exception as e:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Error en asistencia {asistencia.id}: {str(e)}"
                        )
                    )
        
        # Resumen final
        self.stdout.write('\n' + '═' * 100)
        self.stdout.write(self.style.SUCCESS(f'\n✅ PROCESO COMPLETADO'))
        self.stdout.write(f"Total procesadas: {len(asistencias)}")
        self.stdout.write(self.style.SUCCESS(f"Corregidas: {corregidas}"))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"Errores: {errores}"))
        self.stdout.write('═' * 100 + '\n')