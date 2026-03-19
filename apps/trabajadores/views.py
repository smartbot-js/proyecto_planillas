"""
Vistas para el módulo de trabajadores
Gestiona CRUD, importación/exportación CSV, traslados y reportes
"""

from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import csv
import io

from .models import Trabajador, HistorialProyecto, DocumentoTrabajador
from .serializers import TrabajadorSerializer, TrabajadorListSerializer
from .utils import generar_qr_trabajador, parsear_cedula_paraguaya, validar_identificacion_trabajador

from apps.proyectos.models import Proyecto
from apps.core.nicaragua_data import DEPARTAMENTOS
from apps.core.puestos_data import AREAS_TRABAJO
from apps.admin_panel.permissions import PermissionRequiredMixin

from apps.core.puestos_data import AREAS_TRABAJO

# ============================================
# VISTAS WEB (TEMPLATES)
# ============================================

class TrabajadorListView(LoginRequiredMixin, ListView):
    """Vista para listar trabajadores con filtros y búsqueda"""
    model = Trabajador
    template_name = 'trabajadores/lista.html'
    context_object_name = 'trabajadores'
    paginate_by = 20
    
    def get_queryset(self):
        """Obtiene el queryset con filtros aplicados"""
        queryset = Trabajador.objects.filter(eliminado=False).select_related('proyecto_asignado')
        
        # Búsqueda por nombre o cédula
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(nombre__icontains=search_query) |
                Q(apellido__icontains=search_query) |
                Q(numero_cedula__icontains=search_query)
            )
        
        # Filtro por proyecto
        proyecto_id = self.request.GET.get('proyecto')
        if proyecto_id and proyecto_id != 'todos':
            queryset = queryset.filter(proyecto_asignado_id=proyecto_id)
        
        # Filtro por cargo
        cargo = self.request.GET.get('cargo')
        if cargo and cargo != 'todos':
            queryset = queryset.filter(puesto_laboral=cargo)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado and estado != 'todos':
            queryset = queryset.filter(estado=estado)
        
        # Filtro por asegurado
        asegurado = self.request.GET.get('asegurado')
        if asegurado == 'si':
            queryset = queryset.filter(asegurado=True)
        elif asegurado == 'no':
            queryset = queryset.filter(asegurado=False)
        
        # Filtrar por proyectos permitidos según rol
        if not self.request.user.es_administrador():
            proyectos_permitidos = self.request.user.get_proyectos_permitidos()
            queryset = queryset.filter(proyecto_asignado__in=proyectos_permitidos)
        
        return queryset.order_by('-creado_en')
    
    def get_context_data(self, **kwargs):
        """Añade contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        #Proyectos para el filtro
        context['proyectos'] = self.request.user.get_proyectos_permitidos().order_by('nombre')
        
        # context['proyectos'] = Proyecto.objects.filter(
        #     activo=True,
        #     eliminado=False
        # ).order_by('nombre').values_list('nombre', flat=True)        
        
        print(f"PROYECTOOS: {context['proyectos']}")
        # Choices para los filtros
        context['estados'] = Trabajador.Estado.choices
        
        # Estadísticas
        if self.request.user.es_administrador():
            base_qs = Trabajador.objects.filter(eliminado=False)
        else:
            proyectos_permitidos = self.request.user.get_proyectos_permitidos()
            base_qs = Trabajador.objects.filter(eliminado=False, proyecto_asignado__in=proyectos_permitidos)
        
        context['total_trabajadores'] = base_qs.count()
        context['trabajadores_activos'] = base_qs.filter(estado=Trabajador.Estado.ACTIVO).count()
        context['trabajadores_asegurados'] = base_qs.filter(asegurado=True).count()
        
        # Mantener los valores de los filtros
        context['search_query'] = self.request.GET.get('search', '')
        context['proyecto_actual'] = self.request.GET.get('proyecto', 'todos')
        context['cargo_actual'] = self.request.GET.get('cargo', 'todos')
        context['estado_actual'] = self.request.GET.get('estado', 'todos')
        context['asegurado_actual'] = self.request.GET.get('asegurado', 'todos')

        context['trabajadores_inactivos'] = Trabajador.objects.filter(
            eliminado=False,
            estado=Trabajador.Estado.INACTIVO # quitar si se quiere  que salgan todos los estados diferentes a activos
        ).exclude(estado=Trabajador.Estado.ACTIVO).count() 
        
        
        return context


class TrabajadorCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para crear un nuevo trabajador"""
    permission_modulo = 'trabajadores'
    permission_accion = 'crear'
    template_name = 'trabajadores/crear.html'
    
    def get(self, request):
        """Muestra el formulario de creación"""
        proyectos = Proyecto.objects.filter(
            # activo=True,
            eliminado=False
        ).order_by('nombre')
        
        context = {
            'proyectos': proyectos,
            'tipos_sangre': Trabajador.TipoSangre.choices,
            'sexos': Trabajador.Sexo.choices,
            'estados': Trabajador.Estado.choices,
            'today': timezone.now().date(),
            'departamentos': DEPARTAMENTOS,
            'areas_trabajo': AREAS_TRABAJO
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Procesa el formulario de creación"""
        try:
            # Verificar si ya existe un trabajador con esa cédula
            numero_cedula = request.POST.get('numero_cedula', '').strip()
            if numero_cedula:
                # Verificar duplicado activo
                if Trabajador.objects.filter(numero_cedula=numero_cedula, eliminado=False).exists():
                    messages.error(
                        request,
                        f'❌ Ya existe un trabajador registrado con la cédula {numero_cedula}'
                    )
                    return redirect('trabajador_crear')
                
                # Verificar si existe uno eliminado → restaurar
                trabajador_eliminado = Trabajador.objects.filter(
                    numero_cedula=numero_cedula, eliminado=True
                ).first()
                
                if trabajador_eliminado:
                    trabajador_eliminado.eliminado = False
                    trabajador_eliminado.estado = 'activo'
                    trabajador_eliminado.nombre = request.POST.get('nombre', trabajador_eliminado.nombre)
                    trabajador_eliminado.apellido = request.POST.get('apellido', trabajador_eliminado.apellido)
                    trabajador_eliminado.telefono = request.POST.get('telefono', '')
                    trabajador_eliminado.email = request.POST.get('email', '')
                    trabajador_eliminado.direccion = request.POST.get('direccion', '')
                    trabajador_eliminado.departamento = request.POST.get('departamento', '')
                    trabajador_eliminado.municipio = request.POST.get('municipio', '')
                    trabajador_eliminado.puesto_laboral = request.POST.get('puesto_laboral') or request.POST.get('cargo', '')
                    trabajador_eliminado.area_cargo = request.POST.get('area_cargo') or request.POST.get('cargo', '')
                    trabajador_eliminado.contacto_emergencia = request.POST.get('contacto_emergencia', '')
                    trabajador_eliminado.salario_normal = request.POST.get('salario_normal') or 0
                    trabajador_eliminado.tarifa_hora_extra = request.POST.get('tarifa_hora_extra') or 0
                    trabajador_eliminado.fecha_ingreso = request.POST.get('fecha_ingreso') or timezone.now().date()
                    trabajador_eliminado.modificado_por = request.user
                    
                    proyecto_id = request.POST.get('proyecto_asignado')
                    if proyecto_id:
                        trabajador_eliminado.proyecto_asignado = Proyecto.objects.get(id=proyecto_id)
                    
                    trabajador_eliminado.save()
                    
                    messages.success(
                        request,
                        f'✅ Trabajador "{trabajador_eliminado.nombre_completo}" restaurado y actualizado exitosamente.'
                    )
                    return redirect('trabajadores_lista')
            
            trabajador = Trabajador()
            
            # Información personal - Extraer nombre y apellido del nombre completo
            nombre_completo = request.POST.get('nombre_completo', '')
            partes_nombre = nombre_completo.split(' ', 1)
            
            trabajador.nombre = request.POST.get('nombre') or (partes_nombre[0] if partes_nombre else '')
            trabajador.apellido = request.POST.get('apellido') or (partes_nombre[1] if len(partes_nombre) > 1 else '')
            trabajador.numero_cedula = numero_cedula or None
            trabajador.fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            trabajador.sexo = request.POST.get('sexo', 'masculino')
            trabajador.tipo_sangre = request.POST.get('tipo_sangre', '')
            
            # Ubicación
            trabajador.departamento = request.POST.get('departamento', '')
            trabajador.municipio = request.POST.get('municipio', '')
            trabajador.direccion = request.POST.get('direccion', '')
            
            # Contacto
            trabajador.telefono = request.POST.get('telefono', '')
            trabajador.email = request.POST.get('email', '')
            trabajador.contacto_emergencia = request.POST.get('contacto_emergencia', '')
            
            # Laboral
            proyecto_id = request.POST.get('proyecto_asignado')
            if proyecto_id:
                trabajador.proyecto_asignado = Proyecto.objects.get(id=proyecto_id)
            
            trabajador.puesto_laboral = request.POST.get('puesto_laboral') or request.POST.get('cargo', '')
            trabajador.area_cargo = request.POST.get('area_cargo') or request.POST.get('cargo', '')
            trabajador.salario_normal = request.POST.get('salario_normal') or 0
            trabajador.tarifa_hora_extra = request.POST.get('tarifa_hora_extra') or 0
            trabajador.bonos = Decimal(request.POST.get('bonos', '0') or '0')
            trabajador.numero_seguro_social = request.POST.get('numero_seguro_social', '')
            
            # Extras
            trabajador.record_policia = 'record_policia' in request.POST
            trabajador.asegurado = 'asegurado' in request.POST
            trabajador.estado = request.POST.get('estado', 'activo')
            trabajador.fecha_ingreso = request.POST.get('fecha_ingreso') or timezone.now().date()
            trabajador.notas = request.POST.get('notas', '')
            
            # Guardar primero para obtener el ID (necesario para los paths de archivos)
            trabajador.creado_por = request.user
            trabajador.modificado_por = request.user
            trabajador.save()
            
            # ARCHIVOS - Guardar después de tener el ID
            if 'foto' in request.FILES:
                trabajador.foto = request.FILES['foto']
            
            if 'foto_cedula_frontal' in request.FILES:
                trabajador.foto_cedula_frontal = request.FILES['foto_cedula_frontal']
            
            if 'foto_cedula_posterior' in request.FILES:
                trabajador.foto_cedula_posterior = request.FILES['foto_cedula_posterior']
            
            if 'foto_cedula' in request.FILES:
                trabajador.foto_cedula = request.FILES['foto_cedula']
            
            if 'record_policia_doc' in request.FILES:
                trabajador.record_policia_doc = request.FILES['record_policia_doc']
            
            trabajador.save()
            
            # Crear historial de proyecto si fue asignado
            if trabajador.proyecto_asignado:
                HistorialProyecto.objects.create(
                    trabajador=trabajador,
                    proyecto=trabajador.proyecto_asignado,
                    fecha_asignacion=trabajador.fecha_ingreso,
                    creado_por=request.user
                )
            
            messages.success(
                request,
                f'✅ Trabajador "{trabajador.nombre_completo}" creado exitosamente.'
            )
            return redirect('trabajadores_lista')
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al crear el trabajador: {str(e)}'
            )
            return redirect('trabajador_crear')


class TrabajadorDetalleView(LoginRequiredMixin, DetailView):
    """Vista para mostrar el detalle completo de un trabajador"""
    model = Trabajador
    template_name = 'trabajadores/detalle.html'
    context_object_name = 'trabajador'
    
    def get_queryset(self):
        """Filtra trabajadores no eliminados"""
        return Trabajador.objects.filter(eliminado=False).select_related(
            'proyecto_asignado',
            'creado_por',
            'modificado_por'
        )
    
    def get_context_data(self, **kwargs):
        """Añade información adicional al contexto"""
        context = super().get_context_data(**kwargs)
        trabajador = self.object
        
        # Historial de proyectos
        context['historial_proyectos'] = HistorialProyecto.objects.filter(
            trabajador=trabajador
        ).select_related('proyecto', 'creado_por').order_by('-fecha_asignacion')
        
        # Verificar permisos de edición
        context['puede_editar'] = (
            self.request.user.es_administrador or 
            trabajador.creado_por == self.request.user
        )
        
        # Calcular estadísticas
        context['dias_trabajados'] = trabajador.tiempo_servicio
        context['edad'] = trabajador.edad
        
        return context


class TrabajadorEditarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para editar un trabajador existente"""
    permission_modulo = 'trabajadores'
    permission_accion = 'editar'
    template_name = 'trabajadores/editar.html'
    
    def get(self, request, pk):
        """Renderiza el formulario de edición con los datos del trabajador"""
        trabajador = get_object_or_404(Trabajador, pk=pk, eliminado=False)
        
        # Validación de permisos
        if not request.user.es_administrador and trabajador.creado_por != request.user:
            messages.warning(
                request, 
                '⚠️ No tienes permisos suficientes para editar este trabajador.'
            )
            return redirect('trabajadores_lista')
        
        # Obtener proyectos activos
        proyectos = Proyecto.objects.filter(
            # activo=True,
            eliminado=False
        ).order_by('nombre')
        
        context = {
            'trabajador': trabajador,
            'proyectos': proyectos,
            'tipos_sangre': Trabajador.TipoSangre.choices,
            'sexos': Trabajador.Sexo.choices,
            'estados': Trabajador.Estado.choices,
            'departamentos': DEPARTAMENTOS,
            'areas_trabajo': AREAS_TRABAJO,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """Procesa la actualización del trabajador"""
        trabajador = get_object_or_404(Trabajador, pk=pk, eliminado=False)
        
        # Validación de permisos
        if not request.user.es_administrador and trabajador.creado_por != request.user:
            messages.error(
                request,
                '❌ No tienes permisos suficientes para editar este trabajador.'
            )
            return redirect('trabajadores_lista')
        
        try:
            # Validar cédula única
            nuevo_numero_cedula = request.POST.get('numero_cedula')
            if nuevo_numero_cedula and nuevo_numero_cedula != trabajador.numero_cedula:
                if Trabajador.objects.filter(
                    numero_cedula=nuevo_numero_cedula,
                    eliminado=False
                ).exclude(pk=trabajador.pk).exists():
                    messages.error(
                        request,
                        f'❌ Ya existe un trabajador con la cédula {nuevo_numero_cedula}'
                    )
                    return redirect('trabajador_editar', pk=pk)
            
            # ============================================
            # CAMPOS BÁSICOS - CORREGIDO
            # ============================================
            # Leer nombre y apellido directamente del POST
            nombre = request.POST.get('nombre', '').strip()
            apellido = request.POST.get('apellido', '').strip()
            
            if nombre:
                trabajador.nombre = nombre
            if apellido:
                trabajador.apellido = apellido
            
            if nuevo_numero_cedula:
                trabajador.numero_cedula = nuevo_numero_cedula
            
            # Fecha de nacimiento
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            if fecha_nacimiento:
                trabajador.fecha_nacimiento = fecha_nacimiento
            
            # Sexo y tipo de sangre
            trabajador.sexo = request.POST.get('sexo', trabajador.sexo)
            trabajador.tipo_sangre = request.POST.get('tipo_sangre', trabajador.tipo_sangre)
            
            # ============================================
            # UBICACIÓN
            # ============================================
            trabajador.departamento = request.POST.get('departamento', trabajador.departamento)
            trabajador.municipio = request.POST.get('municipio', trabajador.municipio)
            trabajador.direccion = request.POST.get('direccion', trabajador.direccion)
            
            # ============================================
            # CONTACTO
            # ============================================
            trabajador.telefono = request.POST.get('telefono', trabajador.telefono)
            trabajador.email = request.POST.get('email', trabajador.email)
            trabajador.contacto_emergencia = request.POST.get('contacto_emergencia', trabajador.contacto_emergencia)
            
            # ============================================
            # PROYECTO
            # ============================================
            proyecto_id = request.POST.get('proyecto_asignado')
            if proyecto_id:
                nuevo_proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
                if trabajador.proyecto_asignado != nuevo_proyecto:
                    # Cerrar historial anterior
                    if trabajador.proyecto_asignado:
                        HistorialProyecto.objects.filter(
                            trabajador=trabajador,
                            fecha_salida__isnull=True
                        ).update(fecha_salida=timezone.now().date())
                    
                    # Crear nuevo historial
                    HistorialProyecto.objects.create(
                        trabajador=trabajador,
                        proyecto=nuevo_proyecto,
                        fecha_asignacion=timezone.now().date(),
                        motivo='Actualización de proyecto',
                        creado_por=request.user
                    )
                
                trabajador.proyecto_asignado = nuevo_proyecto
            else:
                # Si se desasigna el proyecto
                if trabajador.proyecto_asignado:
                    HistorialProyecto.objects.filter(
                        trabajador=trabajador,
                        fecha_salida__isnull=True
                    ).update(fecha_salida=timezone.now().date())
                trabajador.proyecto_asignado = None
            
            # ============================================
            # DATOS LABORALES
            # ============================================
            trabajador.puesto_laboral = request.POST.get('puesto_laboral', trabajador.puesto_laboral)
            trabajador.area_cargo = request.POST.get('area_cargo', trabajador.area_cargo)
            
            # Salarios - manejar valores vacíos
            salario_normal = request.POST.get('salario_normal')
            if salario_normal:
                trabajador.salario_normal = salario_normal
            
            tarifa_hora_extra = request.POST.get('tarifa_hora_extra')
            if tarifa_hora_extra:
                trabajador.tarifa_hora_extra = tarifa_hora_extra
            
            bonos = request.POST.get('bonos', '0')
            trabajador.bonos = Decimal(bonos) if bonos else Decimal('0')
            
            trabajador.numero_seguro_social = request.POST.get('numero_seguro_social', trabajador.numero_seguro_social)
            trabajador.notas = request.POST.get('notas', trabajador.notas)
            
            # ============================================
            # CHECKBOXES
            # ============================================
            trabajador.record_policia = 'record_policia' in request.POST
            trabajador.asegurado = 'asegurado' in request.POST
            
            # ============================================
            # ESTADO Y FECHA
            # ============================================
            trabajador.estado = request.POST.get('estado', trabajador.estado)
            
            fecha_ingreso = request.POST.get('fecha_ingreso')
            if fecha_ingreso:
                trabajador.fecha_ingreso = fecha_ingreso
            
            # ============================================
            # ARCHIVOS (solo si se suben nuevos)
            # ============================================
            if 'foto' in request.FILES:
                trabajador.foto = request.FILES['foto']
            
            if 'foto_cedula' in request.FILES:
                trabajador.foto_cedula = request.FILES['foto_cedula']
            
            if 'foto_cedula_frontal' in request.FILES:
                trabajador.foto_cedula_frontal = request.FILES['foto_cedula_frontal']
            
            if 'foto_cedula_posterior' in request.FILES:
                trabajador.foto_cedula_posterior = request.FILES['foto_cedula_posterior']
            
            if 'record_policia_doc' in request.FILES:
                trabajador.record_policia_doc = request.FILES['record_policia_doc']
            
            # ============================================
            # AUDITORÍA Y GUARDAR
            # ============================================
            trabajador.modificado_por = request.user
            trabajador.save()
            
            messages.success(
                request,
                f'✅ Trabajador "{trabajador.nombre_completo}" actualizado exitosamente.'
            )
            return redirect('trabajadores_lista')
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al actualizar el trabajador: {str(e)}'
            )
            return redirect('trabajador_editar', pk=pk)

class TrabajadorEliminarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para eliminar (soft delete) un trabajador"""
    permission_modulo = 'trabajadores'
    permission_accion = 'eliminar'

    def post(self, request, pk):
        trabajador = get_object_or_404(Trabajador, pk=pk, eliminado=False)
        
        # Validar permisos (solo administradores)
        if not request.user.es_administrador:
            messages.error(
                request,
                '❌ No tienes permisos para eliminar trabajadores.'
            )
            return redirect('trabajadores_lista')
        
        try:
            trabajador.soft_delete()
            messages.success(
                request,
                f'✅ Trabajador "{trabajador.nombre_completo}" eliminado exitosamente.'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al eliminar el trabajador: {str(e)}'
            )
        
        return redirect('trabajadores_lista')


class TrabajadorTrasladarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para trasladar un trabajador a otro proyecto"""
    permission_modulo = 'trabajadores'
    permission_accion = 'editar'
    
    def post(self, request, pk):
        try:
            trabajador = get_object_or_404(Trabajador, pk=pk)
            proyecto_destino_id = request.POST.get('proyecto_destino')
            motivo = request.POST.get('motivo', '')
            
            if not proyecto_destino_id:
                messages.error(request, 'Debe seleccionar un proyecto destino')
                return redirect('trabajadores_lista')
            
            proyecto_destino = get_object_or_404(Proyecto, pk=proyecto_destino_id)
            
            # Registrar en historial
            if trabajador.proyecto_asignado:
                HistorialProyecto.objects.create(
                    trabajador=trabajador,
                    proyecto=trabajador.proyecto_asignado,
                    fecha_salida=timezone.now().date(),
                    motivo=f"Traslado a {proyecto_destino.nombre}. {motivo}",
                    creado_por=request.user
                )
            
            # Asignar nuevo proyecto
            trabajador.proyecto_asignado = proyecto_destino
            trabajador.save()
            
            # Crear nuevo registro en historial
            HistorialProyecto.objects.create(
                trabajador=trabajador,
                proyecto=proyecto_destino,
                fecha_asignacion=timezone.now().date(),
                motivo=motivo,
                creado_por=request.user
            )
            
            messages.success(
                request,
                f'{trabajador.nombre_completo} trasladado exitosamente a {proyecto_destino.nombre}'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al trasladar el trabajador: {str(e)}'
            )
        
        return redirect('trabajadores_lista')


# ============================================
# IMPORTACIÓN Y EXPORTACIÓN CSV
# ============================================

class TrabajadorImportarCSVView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para importar trabajadores desde archivo CSV - CON SOPORTE AJAX"""
    permission_modulo = 'trabajadores'
    permission_accion = 'crear'

    def _parsear_fecha(self, fecha_str):
        """
        Convierte fechas en múltiples formatos a formato Django (YYYY-MM-DD)
        Soporta: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc.
        """
        if not fecha_str or not fecha_str.strip():
            return None
        
        fecha_str = fecha_str.strip()
        
        # Lista de formatos a intentar
        formatos = [
            '%Y-%m-%d',      # 2024-01-15 (ISO)
            '%d/%m/%Y',      # 15/01/2024
            '%m/%d/%Y',      # 01/15/2024 (US)
            '%d-%m-%Y',      # 15-01-2024
            '%m-%d-%Y',      # 01-15-2024
            '%Y/%m/%d',      # 2024/01/15
            '%d.%m.%Y',      # 15.01.2024
            '%m.%d.%Y',      # 01.15.2024
        ]
        
        for formato in formatos:
            try:
                fecha_parseada = datetime.strptime(fecha_str, formato)
                # Retornar como string ISO para que sea serializable en sesión
                return fecha_parseada.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Si ningún formato funcionó, retornar None
        print(f"No se pudo parsear la fecha: {fecha_str}")
        return None

    def post(self, request):
        # Detectar si es petición AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true'
        
        if 'archivo_csv' not in request.FILES:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'No se ha seleccionado ningún archivo',
                    'errores': ['Por favor, selecciona un archivo CSV para continuar.']
                })
            messages.error(request, '❌ No se ha seleccionado ningún archivo.')
            return redirect('trabajadores_lista')
        
        archivo = request.FILES['archivo_csv']
        
        # Validar que sea CSV
        if not archivo.name.endswith('.csv'):
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'Formato de archivo incorrecto',
                    'errores': [
                        'El archivo debe tener extensión .csv',
                        'Si tu archivo es Excel (.xlsx), guárdalo como "CSV UTF-8 (delimitado por comas)"'
                    ]
                })
            messages.error(request, '❌ El archivo debe ser formato CSV.')
            return redirect('trabajadores_lista')
        
        try:
            # Leer el archivo CSV
            decoded_file = archivo.read().decode('utf-8-sig')  # utf-8-sig para manejar BOM
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # Validar que tenga las columnas requeridas
            columnas_requeridas = ['nombre', 'apellido', 'numero_cedula', 'telefono', 'puesto_laboral']
            columnas_archivo = reader.fieldnames or []
            
            # Limpiar nombres de columnas (espacios, mayúsculas)
            columnas_archivo_limpio = [col.strip().lower() for col in columnas_archivo]
            
            faltantes = [col for col in columnas_requeridas if col not in columnas_archivo_limpio]
            
            if faltantes:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'mensaje': 'El archivo CSV no tiene las columnas requeridas',
                        'errores': [
                            f'Columnas faltantes: {", ".join(faltantes)}',
                            f'Columnas encontradas: {", ".join(columnas_archivo)}',
                            'Descarga la plantilla de ejemplo para ver el formato correcto'
                        ]
                    })
                messages.error(
                    request,
                    f'❌ El archivo CSV no tiene las columnas requeridas. Faltan: {", ".join(faltantes)}'
                )
                return redirect('trabajadores_lista')
            
            # Procesar filas
            trabajadores_nuevos = []
            trabajadores_duplicados = []
            errores = []
            filas_ignoradas = 0
            filas_vacias = 0
            
            for idx, row in enumerate(reader, start=2):  # Empieza en 2 porque 1 es el header
                # Normalizar claves del row (quitar espacios, minúsculas)
                row = {k.strip().lower(): v.strip() if v else '' for k, v in row.items()}
                
                numero_cedula = row.get('numero_cedula', '').strip()
                nombre = row.get('nombre', '').strip()
                
                # IGNORAR FILA DE EJEMPLO
                if numero_cedula.upper() == 'EJEMPLO-123' or nombre.upper() == 'EJEMPLO':
                    filas_ignoradas += 1
                    continue
                
                # Ignorar filas completamente vacías
                if not numero_cedula and not nombre:
                    filas_vacias += 1
                    continue
                
                if not numero_cedula:
                    errores.append(f"Fila {idx}: Número de cédula vacío")
                    continue
                
                # Verificar si ya existe
                if numero_cedula and Trabajador.objects.filter(numero_cedula=numero_cedula, eliminado=False).exists():
                    trabajadores_duplicados.append({
                        'fila': idx,
                        'cedula': numero_cedula,
                        'nombre': f"{row.get('nombre', '')} {row.get('apellido', '')}".strip()
                    })
                    continue
                
                # Validar campos requeridos
                apellido = row.get('apellido', '').strip()
                telefono = row.get('telefono', '').strip()
                puesto_laboral = row.get('puesto_laboral', '').strip()
                
                campos_faltantes = []
                if not nombre:
                    campos_faltantes.append('nombre')
                if not apellido:
                    campos_faltantes.append('apellido')
                if not puesto_laboral:
                    campos_faltantes.append('puesto_laboral')
                
                if campos_faltantes:
                    errores.append(f"Fila {idx}: Campos vacíos ({', '.join(campos_faltantes)}) - Cédula: {numero_cedula}")
                    continue
                
                # Construir contacto de emergencia
                contacto_emergencia = ''
                nombre_contacto = row.get('nombre_contacto_emergencia', '').strip()
                numero_contacto = row.get('numero_contacto_emergencia', '').strip()
                if nombre_contacto or numero_contacto:
                    contacto_emergencia = f"{nombre_contacto} | {numero_contacto}".strip(' |')
                
                # Preparar datos del trabajador
                trabajador_data = {
                    'nombre': nombre,
                    'apellido': apellido,
                    'numero_cedula': numero_cedula or None,
                    'telefono': telefono,
                    'puesto_laboral': puesto_laboral,
                    'area_cargo': row.get('area_cargo', '').strip(),
                    'departamento': row.get('departamento', '').strip(),
                    'municipio': row.get('municipio', '').strip(),
                    'direccion': row.get('direccion', '').strip(),
                    'email': row.get('email', '').strip(),
                    'contacto_emergencia': contacto_emergencia,
                    'fecha_nacimiento': self._parsear_fecha(row.get('fecha_nacimiento', '')),
                    'sexo': row.get('sexo', 'masculino').lower(),
                    'salario_normal': row.get('salario_normal', 0) or 0,
                    'tarifa_hora_extra': row.get('tarifa_hora_extra', 0) or 0,
                    'numero_seguro_social': row.get('numero_seguro_social', '').strip(),
                    'asegurado': row.get('asegurado', '').lower() in ['si', 'sí', 'yes', 'true', '1'],
                    'estado': 'activo',
                    'fecha_ingreso': timezone.now().date(),
                    'creado_por': request.user,
                    'modificado_por': request.user,
                }
                
                # Validar sexo
                if trabajador_data['sexo'] not in ['masculino', 'femenino', 'otro']:
                    trabajador_data['sexo'] = 'masculino'
                
                trabajadores_nuevos.append(trabajador_data)
            
            # Si hay duplicados, pedir confirmación
            if trabajadores_duplicados:
                # Guardar datos en sesión para confirmación
                request.session['trabajadores_importar'] = {
                    'nuevos': trabajadores_nuevos,
                    'duplicados': trabajadores_duplicados,
                    'errores': errores,
                    'ignoradas': filas_ignoradas,
                }
                
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'requiere_confirmacion': True,
                        'nuevos': len(trabajadores_nuevos),
                        'duplicados_lista': trabajadores_duplicados,
                        'errores': errores,
                        'ignorados': filas_ignoradas
                    })
                
                # Renderizar página de confirmación (flujo tradicional)
                return render(request, 'trabajadores/importar_confirmar.html', {
                    'duplicados': trabajadores_duplicados,
                    'nuevos_count': len(trabajadores_nuevos),
                    'errores': errores,
                    'ignoradas': filas_ignoradas,
                })
            
            # Si no hay trabajadores válidos
            if not trabajadores_nuevos:
                if is_ajax:
                    errores_msg = errores if errores else ['No se encontraron datos válidos en el archivo']
                    return JsonResponse({
                        'success': False,
                        'mensaje': 'No se encontraron trabajadores válidos para importar',
                        'errores': errores_msg,
                        'ignorados': filas_ignoradas
                    })
                
                if filas_ignoradas > 0:
                    messages.info(request, f'ℹ️ Se ignoraron {filas_ignoradas} fila(s) de ejemplo.')
                messages.warning(request, '⚠️ No se encontraron trabajadores válidos para importar.')
                return redirect('trabajadores_lista')
            
            # Si no hay duplicados, crear directamente
            creados = self._crear_trabajadores(trabajadores_nuevos)
            
            if is_ajax:
                advertencias = []
                if errores:
                    advertencias.append(f'Se encontraron {len(errores)} filas con errores')
                
                return JsonResponse({
                    'success': True,
                    'creados': creados,
                    'duplicados': 0,
                    'ignorados': filas_ignoradas,
                    'advertencias': advertencias
                })
            
            mensaje_exito = f'✅ Se importaron exitosamente {creados} trabajadores.'
            if filas_ignoradas > 0:
                mensaje_exito += f' Se ignoraron {filas_ignoradas} fila(s) de ejemplo.'
            
            messages.success(request, mensaje_exito)
            
            if errores:
                messages.warning(
                    request,
                    f'⚠️ Se encontraron {len(errores)} errores: {"; ".join(errores[:5])}'
                )
            
            return redirect('trabajadores_lista')
            
        except UnicodeDecodeError:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'Error de codificación en el archivo',
                    'errores': [
                        'El archivo no está en formato UTF-8',
                        'Abre el archivo en Excel y guárdalo como "CSV UTF-8 (delimitado por comas)"',
                        'O usa un editor de texto para guardarlo con codificación UTF-8'
                    ]
                })
            messages.error(request, '❌ Error de codificación. Guarda el archivo como CSV UTF-8.')
            return redirect('trabajadores_lista')
            
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'Error al procesar el archivo',
                    'errores': [str(e)]
                })
            messages.error(
                request,
                f'❌ Error al procesar el archivo: {str(e)}'
            )
            return redirect('trabajadores_lista')
    
    def _crear_trabajadores(self, trabajadores_data):
        """Crea trabajadores en lote y genera QRs automáticamente.
        Si la cédula existe con eliminado=True, restaura el registro."""
        from .utils import generar_qr_trabajador
        
        trabajadores = []
        
        for data in trabajadores_data:
            try:
                cedula = data.get('numero_cedula')
                
                # Intentar restaurar si fue eliminado previamente
                if cedula:
                    eliminado = Trabajador.objects.filter(
                        numero_cedula=cedula, eliminado=True
                    ).first()
                    
                    if eliminado:
                        for campo, valor in data.items():
                            setattr(eliminado, campo, valor)
                        eliminado.eliminado = False
                        eliminado.estado = 'activo'
                        eliminado.save()
                        trabajadores.append(eliminado)
                        continue
                
                trabajador = Trabajador(**data)
                trabajador.save()
                
                # Generar QR automáticamente
                try:
                    generar_qr_trabajador(trabajador)
                    trabajador.save(update_fields=['codigo_qr'])
                except Exception as e:
                    print(f"Error al generar QR para {trabajador.numero_cedula}: {str(e)}")
                
                trabajadores.append(trabajador)
            except Exception as e:
                print(f"Error al crear trabajador: {str(e)}")
                continue
        
        return len(trabajadores)


class TrabajadorImportarConfirmarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para confirmar importación con duplicados - CON SOPORTE AJAX"""
    permission_modulo = 'trabajadores'
    permission_accion = 'crear'

    def post(self, request):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true'
        accion = request.POST.get('accion')
        
        if accion not in ['confirmar', 'cancelar']:
            if is_ajax:
                return JsonResponse({'success': False, 'mensaje': 'Acción inválida'})
            messages.error(request, '❌ Acción inválida.')
            return redirect('trabajadores_lista')
        
        # Recuperar datos de la sesión
        datos_importar = request.session.get('trabajadores_importar')
        
        if not datos_importar:
            if is_ajax:
                return JsonResponse({'success': False, 'mensaje': 'No se encontraron datos para importar. Intenta subir el archivo nuevamente.'})
            messages.error(request, '❌ No se encontraron datos para importar.')
            return redirect('trabajadores_lista')
        
        if accion == 'cancelar':
            del request.session['trabajadores_importar']
            if is_ajax:
                return JsonResponse({'success': True, 'mensaje': 'Importación cancelada'})
            messages.info(request, 'ℹ️ Importación cancelada.')
            return redirect('trabajadores_lista')
        
        # Confirmar: crear trabajadores omitiendo duplicados
        from .utils import generar_qr_trabajador
        
        trabajadores_nuevos = datos_importar['nuevos']
        duplicados_count = len(datos_importar['duplicados'])
        
        creados = 0
        qr_generados = 0
        
        for data in trabajadores_nuevos:
            try:
                # Crear trabajador
                trabajador = Trabajador(**data)
                trabajador.save()
                creados += 1
                
                # Generar QR automáticamente
                try:
                    generar_qr_trabajador(trabajador)
                    trabajador.save(update_fields=['codigo_qr'])
                    qr_generados += 1
                except Exception as qr_error:
                    print(f"Error generando QR para {trabajador.numero_cedula}: {str(qr_error)}")
                
            except Exception as e:
                print(f"Error creando trabajador: {str(e)}")
                continue
        
        # Limpiar sesión
        del request.session['trabajadores_importar']
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'creados': creados,
                'duplicados': duplicados_count,
                'qr_generados': qr_generados
            })
        
        messages.success(
            request,
            f'✅ Se importaron {creados} trabajadores con {qr_generados} códigos QR generados. '
            f'Se omitieron {duplicados_count} duplicados.'
        )
        
        if datos_importar['errores']:
            messages.warning(
                request,
                f'⚠️ Se encontraron {len(datos_importar["errores"])} errores durante la importación.'
            )
        
        return redirect('trabajadores_lista')

def trabajadores_exportar(request):
    """Exporta la lista completa de trabajadores a CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="trabajadores_exportados.csv"'
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response)
    
    # Header con todas las columnas
    writer.writerow([
        'nombre',
        'apellido',
        'numero_cedula',
        'fecha_nacimiento',
        'sexo',
        'telefono',
        'email',
        'direccion',
        'departamento',
        'municipio',
        'nombre_contacto_emergencia',
        'numero_contacto_emergencia',
        'puesto_laboral',
        'area_cargo',
        'salario_normal',
        'tarifa_hora_extra',
        'numero_seguro_social',
        'asegurado',
        'proyecto',
        'estado',
        'fecha_ingreso'
    ])
    
    # Exportar todos los trabajadores no eliminados
    trabajadores = Trabajador.objects.filter(eliminado=False).select_related('proyecto_asignado')
    
    for t in trabajadores:
        # Separar contacto de emergencia
        contacto_nombre = ''
        contacto_numero = ''
        if t.contacto_emergencia:
            # Formato esperado: "Nombre | Número" o "Nombre - Número"
            if '|' in t.contacto_emergencia:
                partes = t.contacto_emergencia.split('|')
                contacto_nombre = partes[0].strip() if len(partes) > 0 else ''
                contacto_numero = partes[1].strip() if len(partes) > 1 else ''
            elif '-' in t.contacto_emergencia:
                partes = t.contacto_emergencia.split('-')
                contacto_nombre = partes[0].strip() if len(partes) > 0 else ''
                contacto_numero = partes[1].strip() if len(partes) > 1 else ''
            else:
                contacto_nombre = t.contacto_emergencia
        
        writer.writerow([
            t.nombre,
            t.apellido,
            t.numero_cedula,
            t.fecha_nacimiento.strftime('%Y-%m-%d') if t.fecha_nacimiento else '',
            t.sexo,
            t.telefono,
            t.email or '',
            t.direccion,
            t.departamento,
            t.municipio,
            contacto_nombre,
            contacto_numero,
            t.puesto_laboral,
            t.area_cargo,
            float(t.salario_normal) if t.salario_normal else 0,
            float(t.tarifa_hora_extra) if t.tarifa_hora_extra else 0,
            t.numero_seguro_social or '',
            'si' if t.asegurado else 'no',
            t.proyecto_asignado.nombre if t.proyecto_asignado else '',
            t.estado,
            t.fecha_ingreso.strftime('%Y-%m-%d') if t.fecha_ingreso else ''
        ])
    
    return response


def trabajadores_plantilla_csv(request):
    """Genera una plantilla CSV actualizada con ejemplos y formato correcto"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="plantilla_trabajadores.csv"'
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response)
    
    # Header con campos separados
    writer.writerow([
        'nombre',
        'apellido',
        'numero_cedula',
        'fecha_nacimiento',
        'sexo',
        'telefono',
        'email',
        'direccion',
        'departamento',
        'municipio',
        'nombre_contacto_emergencia',
        'numero_contacto_emergencia',
        'puesto_laboral',
        'area_cargo',
        'salario_normal',
        'tarifa_hora_extra',
        'numero_seguro_social',
        'asegurado'
    ])
    
    # Fila de ejemplo (será ignorada en la importación)
    writer.writerow([
        'EJEMPLO',
        'IGNORAR',
        'EJEMPLO-123',
        '1990-01-15',
        'masculino',
        '0981234567',
        'ejemplo@email.com',
        'Av. Principal 123',
        'Central',
        'Asunción',
        'María Pérez',
        '0982345678',
        'Operario',
        'Albañilería',
        '2500000',
        '20000',
        'SS123456',
        'si'
    ])
    
    return response

class TrabajadorCambiarEstadoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para cambiar el estado de un trabajador"""
    permission_modulo = 'trabajadores'
    permission_accion = 'editar'
    
    def post(self, request, pk):
        trabajador = get_object_or_404(Trabajador, pk=pk)
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado in ['activo', 'inactivo', 'suspendido', 'retirado']:
            trabajador.cambiar_estado(nuevo_estado)
            messages.success(
                request,
                f'Estado del trabajador {trabajador.nombre_completo} cambiado a {trabajador.get_estado_display()}'
            )
        else:
            messages.error(request, 'Estado inválido')
        
        return redirect('trabajadores_lista')
# ============================================
# API REST (PARA APP MÓVIL)
# ============================================

from .utils import generar_qr_trabajador, validar_identificacion_trabajador

class TrabajadorGenerarQRView(LoginRequiredMixin, View):
    """Vista para generar o regenerar código QR del trabajador"""
    
    def post(self, request, pk):
        trabajador = get_object_or_404(Trabajador, pk=pk, eliminado=False)
        
        try:
            # Generar/regenerar QR
            generar_qr_trabajador(trabajador)
            trabajador.save(update_fields=['codigo_qr'])
            
            messages.success(
                request,
                f'✅ Código QR generado exitosamente para {trabajador.nombre_completo}'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al generar código QR: {str(e)}'
            )
        
        return redirect('trabajador_detalle', pk=pk)


class TrabajadorRegenerarTodosQRView(LoginRequiredMixin, View):
    """Vista para regenerar QR de todos los trabajadores que no lo tienen"""
    
    def post(self, request):
        # Solo administradores
        if not request.user.es_administrador:
            messages.error(request, '❌ No tienes permisos para esta acción.')
            return redirect('trabajadores_lista')
        
        try:
            # Obtener trabajadores sin QR
            trabajadores_sin_qr = Trabajador.objects.filter(
                eliminado=False,
                codigo_qr__in=['', None]
            )
            
            total = trabajadores_sin_qr.count()
            exitosos = 0
            errores = 0
            
            for trabajador in trabajadores_sin_qr:
                try:
                    generar_qr_trabajador(trabajador)
                    trabajador.save(update_fields=['codigo_qr'])
                    exitosos += 1
                except Exception as e:
                    errores += 1
                    print(f"Error generando QR para {trabajador.numero_cedula}: {str(e)}")
            
            if exitosos > 0:
                messages.success(
                    request,
                    f'✅ Se generaron {exitosos} códigos QR exitosamente.'
                )
            
            if errores > 0:
                messages.warning(
                    request,
                    f'⚠️ {errores} códigos QR no pudieron generarse.'
                )
            
            if total == 0:
                messages.info(
                    request,
                    'ℹ️ Todos los trabajadores ya tienen código QR generado.'
                )
        
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al regenerar códigos QR: {str(e)}'
            )
        
        return redirect('trabajadores_lista')  

class TrabajadorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el API REST de trabajadores
    Usado por la aplicación móvil
    """
    queryset = Trabajador.objects.filter(eliminado=False)
    serializer_class = TrabajadorSerializer
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'list':
            return TrabajadorListSerializer
        return TrabajadorSerializer
    
    def get_queryset(self):
        """Filtra el queryset según parámetros"""
        queryset = super().get_queryset()
        
        # Filtro por proyecto
        proyecto_id = self.request.query_params.get('proyecto')
        if proyecto_id:
            queryset = queryset.filter(proyecto_asignado_id=proyecto_id)
        
        # Filtro por estado
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Búsqueda
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(numero_cedula__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='por-cedula/(?P<cedula>[^/]+)')
    def por_cedula(self, request, cedula=None):
        """
        Endpoint para buscar trabajador por número de cédula
        Usado por la app móvil para escaneo de asistencias
        Acepta cédula con o sin guiones
        """
        from .utils import buscar_trabajador_por_cedula
        
        trabajador = buscar_trabajador_por_cedula(cedula)
        
        if trabajador:
            serializer = self.get_serializer(trabajador)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Trabajador no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Retorna solo trabajadores activos"""
        trabajadores = self.get_queryset().filter(estado=Trabajador.Estado.ACTIVO)
        serializer = self.get_serializer(trabajadores, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='validar-identificacion')
    def validar_identificacion(self, request):
        """
        Endpoint unificado para validar QR o código de barras de cédula
        Detecta automáticamente el tipo de código
        
        POST /api/trabajadores/validar-identificacion/
        Body: {"codigo": "1010124036"} o {"codigo": "0362284301��������..."}
        
        Response:
        {
            "valido": true,
            "tipo_codigo": "QR_GENERADO" o "CEDULA_FISICA",
            "trabajador": {...},
            "datos_extraidos": {...}  // Solo si es cédula física
        }
        """
        codigo = request.data.get('codigo')
        
        if not codigo:
            return Response(
                {'error': 'Debe proporcionar el código escaneado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        resultado = validar_identificacion_trabajador(codigo)
        
        if resultado['valido']:
            serializer = self.get_serializer(resultado['trabajador'])
            
            response_data = {
                'valido': True,
                'tipo_codigo': resultado['tipo_codigo'],
                'trabajador': serializer.data
            }
            
            # Si es cédula física, incluir datos extraídos
            if resultado['tipo_codigo'] == 'CEDULA_FISICA' and 'datos_extraidos' in resultado:
                response_data['datos_extraidos'] = resultado.get('datos_extraidos')
            
            return Response(response_data)
        else:
            return Response(
                {
                    'valido': False,
                    'tipo_codigo': resultado.get('tipo_codigo'),
                    'error': resultado['error']
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], url_path='parsear-cedula')
    def parsear_cedula(self, request):
        """
        Endpoint para parsear código de barras de cédula sin validar trabajador
        Útil para debugging en la app móvil
        
        POST /api/trabajadores/parsear-cedula/
        Body: {"codigo_barras": "0362284301��������..."}
        """
        codigo_barras = request.data.get('codigo_barras')
        
        if not codigo_barras:
            return Response(
                {'error': 'Debe proporcionar codigo_barras'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        resultado = parsear_cedula_paraguaya(codigo_barras)
        resultado = "FALTA FUNCION PARA PARSEAR LA CEDULA"
        return Response(resultado)