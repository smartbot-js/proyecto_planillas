from django.core.management.base import BaseCommand
from apps.usuarios.models import Usuario
from apps.trabajadores.models import Trabajador
from apps.trabajadores.utils import generar_qr_trabajador


class Command(BaseCommand):
    help = 'Crea trabajador para cada usuario que no tenga uno'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo simular')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write('\n🔄 Migración: Usuarios → Trabajadores\n')

        creados = 0
        existentes = 0

        for usuario in Usuario.objects.filter(is_active=True):
            if Trabajador.objects.filter(email=usuario.email, eliminado=False).exists():
                existentes += 1
                continue

            partes = usuario.nombre_completo.split(' ', 1)
            nombre = partes[0]
            apellido = partes[1] if len(partes) > 1 else ''

            if dry_run:
                self.stdout.write(f'  [SIMULADO] {usuario.nombre_completo}')
                creados += 1
                continue

            try:
                t = Trabajador.objects.create(
                    nombre=nombre, apellido=apellido,
                    numero_cedula=f'USR-{usuario.id}', email=usuario.email,
                    puesto_laboral='', area_cargo='',
                    salario_normal=0, tarifa_hora_extra=0, estado='activo',
                )
                try:
                    generar_qr_trabajador(t)
                    t.save(update_fields=['codigo_qr'])
                except Exception:
                    pass
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ {usuario.nombre_completo} → Trabajador #{t.id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ {usuario.nombre_completo}: {e}'))

        self.stdout.write(f'\nExistentes: {existentes} | Creados: {creados}')
        if not dry_run and creados:
            self.stdout.write('\n⚠️  Completar manualmente: cédula, puesto, área, salario, proyecto')
            