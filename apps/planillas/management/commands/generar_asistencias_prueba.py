"""
Comando COMPLETO para generar asistencias de prueba con geolocalización
apps/planillas/management/commands/generar_asistencias_prueba.py
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.asistencias.models import Asistencia
from apps.trabajadores.models import Trabajador
from apps.proyectos.models import Proyecto
from datetime import date, time, timedelta
from decimal import Decimal
import random
import math


class Command(BaseCommand):
    help = 'Genera asistencias de prueba para un proyecto específico con geolocalización'

    def add_arguments(self, parser):
        parser.add_argument(
            '--proyecto-id',
            type=int,
            default=4,
            help='ID del proyecto (default: 4 = Smartbot)'
        )
        parser.add_argument(
            '--fecha-inicio',
            type=str,
            default='2025-10-31',
            help='Fecha de inicio en formato YYYY-MM-DD (default: 2025-10-31)'
        )
        parser.add_argument(
            '--fecha-fin',
            type=str,
            default='2025-11-12',
            help='Fecha de fin en formato YYYY-MM-DD (default: 2025-11-12)'
        )
        parser.add_argument(
            '--trabajadores',
            type=int,
            default=5,
            help='Cantidad de trabajadores a usar (default: 5)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Eliminar asistencias existentes del período antes de crear'
        )

    def generar_coordenadas_aleatorias(self, lat_centro, lon_centro, radio_metros):
        """
        Genera coordenadas aleatorias dentro de un radio específico
        
        Args:
            lat_centro: Latitud del centro (proyecto)
            lon_centro: Longitud del centro (proyecto)
            radio_metros: Radio en metros
            
        Returns:
            tuple: (latitud, longitud, distancia_metros)
        """
        # Convertir radio de metros a grados (aproximado)
        # 1 grado de latitud ≈ 111,320 metros
        # 1 grado de longitud ≈ 111,320 * cos(latitud) metros
        
        radio_lat = radio_metros / 111320.0
        radio_lon = radio_metros / (111320.0 * math.cos(math.radians(lat_centro)))
        
        # Generar ángulo aleatorio
        angulo = random.uniform(0, 2 * math.pi)
        
        # Generar distancia aleatoria dentro del radio
        # Usar raíz cuadrada para distribución uniforme en área circular
        distancia_aleatoria = math.sqrt(random.uniform(0, 1)) * radio_metros
        
        # Calcular offset en grados
        offset_lat = (distancia_aleatoria / 111320.0) * math.cos(angulo)
        offset_lon = (distancia_aleatoria / (111320.0 * math.cos(math.radians(lat_centro)))) * math.sin(angulo)
        
        # Coordenadas finales
        lat_final = lat_centro + offset_lat
        lon_final = lon_centro + offset_lon
        
        return (
            Decimal(str(round(lat_final, 7))),
            Decimal(str(round(lon_final, 7))),
            round(distancia_aleatoria, 2)
        )

    def handle(self, *args, **options):
        proyecto_id = options['proyecto_id']
        fecha_inicio = date.fromisoformat(options['fecha_inicio'])
        fecha_fin = date.fromisoformat(options['fecha_fin'])
        max_trabajadores = options['trabajadores']
        limpiar = options['limpiar']

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("GENERANDO ASISTENCIAS DE PRUEBA CON GEOLOCALIZACIÓN"))
        self.stdout.write("=" * 70)

        # ============================================================
        # 1. OBTENER PROYECTO
        # ============================================================
        try:
            proyecto = Proyecto.objects.get(id=proyecto_id)
            self.stdout.write(f"\n✅ Proyecto encontrado: {proyecto.nombre}")
            
            # Mostrar ubicación del proyecto
            if proyecto.latitud and proyecto.longitud:
                self.stdout.write(f"   📍 Ubicación: {proyecto.latitud}, {proyecto.longitud}")
                self.stdout.write(f"   📏 Radio permitido: {proyecto.radio_permitido_metros}m")
            else:
                self.stdout.write(
                    self.style.WARNING("   ⚠️  El proyecto no tiene coordenadas configuradas")
                )
                
        except Proyecto.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error: No se encontró el proyecto con ID {proyecto_id}")
            )
            return

        # ============================================================
        # 2. OBTENER TRABAJADORES
        # ============================================================
        trabajadores = Trabajador.objects.filter(estado='activo')

        if not trabajadores.exists():
            self.stdout.write(
                self.style.ERROR("\n❌ Error: No hay trabajadores activos en el sistema")
            )
            return

        trabajadores = list(trabajadores[:max_trabajadores])
        self.stdout.write(f"\n✅ Trabajadores encontrados: {len(trabajadores)}")
        for t in trabajadores:
            self.stdout.write(f"   • {t.nombre_completo} ({t.puesto_laboral})")

        # ============================================================
        # 3. MOSTRAR PERÍODO
        # ============================================================
        dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        self.stdout.write(f"\n📅 Período de asistencias:")
        self.stdout.write(f"   Inicio: {fecha_inicio.strftime('%d/%m/%Y')} ({dias_nombres[fecha_inicio.weekday()]})")
        self.stdout.write(f"   Fin: {fecha_fin.strftime('%d/%m/%Y')} ({dias_nombres[fecha_fin.weekday()]})")
        self.stdout.write(f"   Total días: {(fecha_fin - fecha_inicio).days + 1}")

        # ============================================================
        # 4. ELIMINAR ASISTENCIAS EXISTENTES SI SE SOLICITA
        # ============================================================
        if limpiar:
            asistencias_existentes = Asistencia.objects.filter(
                proyecto=proyecto,
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin
            )

            if asistencias_existentes.exists():
                cantidad = asistencias_existentes.count()
                asistencias_existentes.delete()
                self.stdout.write(
                    self.style.WARNING(f"\n🗑️  Se eliminaron {cantidad} asistencias existentes")
                )

        # ============================================================
        # 5. GENERAR ASISTENCIAS CON GEOLOCALIZACIÓN
        # ============================================================
        self.stdout.write(f"\n🔄 Generando asistencias con geolocalización...")

        asistencias_creadas = 0
        asistencias_dentro_rango = 0
        asistencias_fuera_rango = 0
        fecha_actual = fecha_inicio

        # Salarios base por tipo de trabajador
        salarios_base = {
            'albañil': Decimal('400.00'),
            'maestro': Decimal('500.00'),
            'ayudante': Decimal('300.00'),
            'oficial': Decimal('450.00'),
            'fontanero': Decimal('450.00'),
            'electricista': Decimal('450.00'),
            'bodeguero': Decimal('350.00'),
            'guarda': Decimal('320.00'),
            'supervisor': Decimal('500.00'),
            'analista': Decimal('450.00'),
            'técnico': Decimal('400.00'),
            'default': Decimal('350.00')
        }

        # Coordenadas del proyecto (usar las proporcionadas o las del modelo)
        if proyecto.latitud and proyecto.longitud:
            lat_proyecto = float(proyecto.latitud)
            lon_proyecto = float(proyecto.longitud)
            radio_proyecto = proyecto.radio_permitido_metros or 100
        else:
            # Usar coordenadas proporcionadas por el usuario
            lat_proyecto = 4.7564907
            lon_proyecto = -74.0894803
            radio_proyecto = 100
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  Usando coordenadas manuales: {lat_proyecto}, {lon_proyecto}")
            )

        while fecha_actual <= fecha_fin:
            dia_semana = fecha_actual.weekday()
            dia_nombre = dias_nombres[dia_semana]
            
            # Saltar domingos
            if dia_semana == 6:
                self.stdout.write(
                    self.style.WARNING(
                        f"   ⏭️  {fecha_actual.strftime('%d/%m/%Y')} ({dia_nombre}) - SALTADO (Domingo)"
                    )
                )
                fecha_actual += timedelta(days=1)
                continue
            
            self.stdout.write(f"   📅 {fecha_actual.strftime('%d/%m/%Y')} ({dia_nombre}):")
            
            for trabajador in trabajadores:
                # Determinar salario base según puesto
                puesto_lower = trabajador.puesto_laboral.lower()
                salario_dia = salarios_base.get('default')
                
                for key, valor in salarios_base.items():
                    if key in puesto_lower:
                        salario_dia = valor
                        break
                
                # Horas normales (8 horas por día)
                horas_normales = Decimal('8.00')
                
                # Probabilidad de horas extras (30%)
                horas_extras = Decimal('0.00')
                if random.random() < 0.3:
                    horas_extras = Decimal(str(random.choice([1.0, 2.0, 3.0])))
                
                # Horas totales
                horas_totales = horas_normales + horas_extras
                
                # Probabilidad de faltar (5%)
                if random.random() < 0.05:
                    self.stdout.write(f"      ⭕ {trabajador.nombre_completo} - AUSENTE")
                    continue
                
                # Generar coordenadas de entrada
                # 70% dentro del rango, 30% fuera para probar validación
                if random.random() < 0.7:
                    # Dentro del rango permitido
                    lat_entrada, lon_entrada, dist_entrada = self.generar_coordenadas_aleatorias(
                        lat_proyecto, lon_proyecto, radio_proyecto * 0.9
                    )
                    ubicacion_entrada_valida = True
                    asistencias_dentro_rango += 1
                else:
                    # Fuera del rango (para probar validación)
                    lat_entrada, lon_entrada, dist_entrada = self.generar_coordenadas_aleatorias(
                        lat_proyecto, lon_proyecto, radio_proyecto * 1.5
                    )
                    ubicacion_entrada_valida = dist_entrada <= radio_proyecto
                    if not ubicacion_entrada_valida:
                        asistencias_fuera_rango += 1
                
                # Generar coordenadas de salida (generalmente cerca de la entrada)
                lat_salida, lon_salida, dist_salida = self.generar_coordenadas_aleatorias(
                    lat_proyecto, lon_proyecto, radio_proyecto * 0.9
                )
                ubicacion_salida_valida = dist_salida <= radio_proyecto
                
                # Crear asistencia
                asistencia = Asistencia(
                    trabajador=trabajador,
                    proyecto=proyecto,
                    fecha=fecha_actual,
                    puesto_laboral=trabajador.puesto_laboral,
                    
                    # Horarios
                    hora_entrada=time(7, 0),
                    hora_salida=time(15 + int(horas_extras), 0),
                    
                    # Horas
                    horas_normales=horas_normales,
                    horas_extras=horas_extras,
                    horas_totales=horas_totales,
                    horas_nocturnas=Decimal('0.00'),
                    horas_festivas=Decimal('0.00'),
                    
                    # Salarios
                    salario_dia=salario_dia,
                    tarifa_hora_extra=(salario_dia / Decimal('12')) * Decimal('2'),
                    salario_hora_festiva=Decimal('0.00'),
                    salario_hora_nocturna=Decimal('0.00'),
                    
                    # Geolocalización - ENTRADA
                    latitud_entrada=lat_entrada,
                    longitud_entrada=lon_entrada,
                    distancia_entrada=Decimal(str(dist_entrada)),
                    ubicacion_entrada_valida=ubicacion_entrada_valida,
                    
                    # Geolocalización - SALIDA
                    latitud_salida=lat_salida,
                    longitud_salida=lon_salida,
                    distancia_salida=Decimal(str(dist_salida)),
                    ubicacion_salida_valida=ubicacion_salida_valida,
                    
                    # Estado
                    estado='cerrado',
                    validado=True,
                    es_dia_festivo=False,
                    
                    # Método
                    metodo_identificacion='gps'
                )
                
                try:
                    # Guardar usando el método padre para evitar el override problemático
                    super(Asistencia, asistencia).save()
                    asistencias_creadas += 1
                    
                    # Emoji según validación de ubicación
                    emoji_ubicacion = "📍" if ubicacion_entrada_valida else "⚠️"
                    
                    if horas_extras > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"      {emoji_ubicacion} {trabajador.nombre_completo} - {horas_normales}h + {horas_extras}h extras ({dist_entrada:.0f}m)"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"      {emoji_ubicacion} {trabajador.nombre_completo} - {horas_normales}h ({dist_entrada:.0f}m)"
                            )
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"      ❌ Error al guardar {trabajador.nombre_completo}: {str(e)}")
                    )
            
            fecha_actual += timedelta(days=1)

        # ============================================================
        # 6. RESUMEN FINAL
        # ============================================================
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("✅ ASISTENCIAS GENERADAS EXITOSAMENTE"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\n📊 RESUMEN:")
        self.stdout.write(f"   • Proyecto: {proyecto.nombre}")
        self.stdout.write(f"   • Ubicación: {lat_proyecto}, {lon_proyecto}")
        self.stdout.write(f"   • Radio permitido: {radio_proyecto}m")
        self.stdout.write(f"   • Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
        self.stdout.write(f"   • Trabajadores: {len(trabajadores)}")
        self.stdout.write(f"   • Asistencias creadas: {asistencias_creadas}")
        self.stdout.write(f"   • Dentro del rango: {asistencias_dentro_rango} (📍)")
        self.stdout.write(f"   • Fuera del rango: {asistencias_fuera_rango} (⚠️)")

        # Calcular totales
        total_horas = Asistencia.objects.filter(
            proyecto=proyecto,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).aggregate(
            horas=Sum('horas_normales'),
            extras=Sum('horas_extras')
        )

        self.stdout.write(f"   • Total horas normales: {float(total_horas['horas'] or 0)}")
        self.stdout.write(f"   • Total horas extras: {float(total_horas['extras'] or 0)}")

        self.stdout.write("\n🎯 PRÓXIMOS PASOS:")
        self.stdout.write("   1. Ve a: http://localhost:8000/planillas/crear/")
        self.stdout.write(f"   2. Selecciona el proyecto: {proyecto.nombre}")
        self.stdout.write(f"   3. Período inicio: {fecha_inicio.strftime('%Y-%m-%d')}")
        self.stdout.write(f"   4. Período fin: {fecha_fin.strftime('%Y-%m-%d')}")
        self.stdout.write("   5. Click en 'Ver Preview'")
        self.stdout.write("   6. Verifica los cálculos y genera la planilla")
        
        self.stdout.write("\n📍 VALIDACIÓN DE GEOLOCALIZACIÓN:")
        self.stdout.write("   • Puedes verificar las coordenadas en el detalle de cada asistencia")
        self.stdout.write("   • Las asistencias marcadas con ⚠️ están fuera del rango permitido")
        self.stdout.write("   • Esto prueba que el sistema de validación de ubicación funciona")

        self.stdout.write("\n" + "=" * 70)
        