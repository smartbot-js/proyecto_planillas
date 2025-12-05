from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from apps.contratistas.models import ContratoProyecto, AvaluoContratista


class Command(BaseCommand):
    help = 'Recalcula los porcentajes de avance de todos los avalúos'

    def handle(self, *args, **kwargs):
        contratos = ContratoProyecto.objects.filter(eliminado=False)
        
        total_contratos = 0
        total_avaluos_corregidos = 0
        
        for contrato in contratos:
            self.stdout.write(f"\nProcesando contrato: {contrato.codigo}")
            
            # Obtener avalúos ordenados por fecha
            avaluos = contrato.avaluos.filter(eliminado=False).order_by('fecha_pago', 'id')
            
            if not avaluos.exists():
                continue
            
            total_contratos += 1
            suma_acumulada = Decimal('0')
            
            for avaluo in avaluos:
                # Sumar el monto actual
                suma_acumulada += avaluo.monto_cordobas
                
                # Calcular porcentaje acumulado
                if contrato.valor_contrato > 0:
                    porcentaje_correcto = (suma_acumulada / contrato.valor_contrato) * 100
                    porcentaje_correcto = round(porcentaje_correcto, 2)
                else:
                    porcentaje_correcto = Decimal('0')
                
                # Si es diferente, actualizar
                if avaluo.porcentaje_avance != porcentaje_correcto:
                    self.stdout.write(
                        f"  - {avaluo.codigo}: {avaluo.porcentaje_avance}% → {porcentaje_correcto}%"
                    )
                    avaluo.porcentaje_avance = porcentaje_correcto
                    avaluo.save(update_fields=['porcentaje_avance'])
                    total_avaluos_corregidos += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Proceso completado:\n"
                f"  - Contratos procesados: {total_contratos}\n"
                f"  - Avalúos corregidos: {total_avaluos_corregidos}"
            )
        )