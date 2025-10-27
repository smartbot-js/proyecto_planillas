import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.proyectos.models import Proyecto
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Reorganiza los archivos de proyectos en carpetas individuales'

    def handle(self, *args, **options):
        proyectos = Proyecto.objects.all()
        media_root = settings.MEDIA_ROOT
        
        self.stdout.write(self.style.SUCCESS(f'Reorganizando archivos de {proyectos.count()} proyectos...'))
        
        for proyecto in proyectos:
            proyecto_slug = slugify(proyecto.nombre)
            self.stdout.write(f'\nProcesando: {proyecto.nombre}')
            
            # Crear directorios del proyecto
            directorios = [
                os.path.join(media_root, 'proyectos', proyecto_slug, 'contratos'),
                os.path.join(media_root, 'proyectos', proyecto_slug, 'avaluos'),
                os.path.join(media_root, 'proyectos', proyecto_slug, 'presupuestos'),
                os.path.join(media_root, 'proyectos', proyecto_slug, 'imagenes'),
            ]
            
            for directorio in directorios:
                os.makedirs(directorio, exist_ok=True)
            
            # Mover archivos existentes
            archivos = [
                ('archivo_contrato', 'contratos'),
                ('archivo_avaluo', 'avaluos'),
                ('archivo_presupuesto', 'presupuestos'),
                ('imagen_proyecto', 'imagenes'),
            ]
            
            for campo, carpeta in archivos:
                archivo = getattr(proyecto, campo)
                if archivo and archivo.name:
                    old_path = os.path.join(media_root, archivo.name)
                    if os.path.exists(old_path):
                        filename = os.path.basename(archivo.name)
                        new_path = os.path.join('proyectos', proyecto_slug, carpeta, filename)
                        new_full_path = os.path.join(media_root, new_path)
                        
                        # Mover archivo
                        shutil.move(old_path, new_full_path)
                        
                        # Actualizar referencia en la base de datos
                        setattr(proyecto, campo, new_path)
                        self.stdout.write(f'  ✓ Movido: {campo}')
            
            proyecto.save()
            self.stdout.write(self.style.SUCCESS(f'  ✅ Completado: {proyecto.nombre}'))
        
        self.stdout.write(self.style.SUCCESS('\n¡Reorganización completada!'))