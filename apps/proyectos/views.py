from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import json

from apps.contratistas.models import Contratista, AvaluoContratista, ContratoProyecto

from .models import Proyecto
from apps.usuarios.models import Usuario
from apps.trabajadores.models import Trabajador
from apps.asistencias.models import Asistencia # <--- 1. IMPORTAR ASISTENCIA
from apps.trabajadores.models import Trabajador, HistorialProyecto
from apps.core.nicaragua_data import DEPARTAMENTOS
from apps.admin_panel.permissions import PermissionRequiredMixin

from datetime import time

class ProyectoListView(LoginRequiredMixin, ListView):
    """Vista para listar todos los proyectos"""
    model = Proyecto
    template_name = 'proyectos/lista.html'
    context_object_name = 'proyectos'
    paginate_by = 12
    
    def get_queryset(self):
        # Filtrar por proyectos permitidos según rol
        queryset = self.request.user.get_proyectos_permitidos().select_related('supervisor')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ubicacion__icontains=search)
            )
        
        estado = self.request.GET.get('estado')
        if estado and estado != 'todos':
            queryset = queryset.filter(estado=estado)
        
        return queryset
        
    def get_context_data(self, **kwargs):
        """Agrega datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        context['estados'] = Proyecto.Estado.choices
        context['estado_actual'] = self.request.GET.get('estado', 'todos')
        context['search_query'] = self.request.GET.get('search', '')
        
        # --- INICIO DE CORRECCIÓN ---
        
        # Queryset base para eficiencia
        base_queryset = Proyecto.objects.filter(eliminado=False)
        
        # Estadísticas (Usando los estados de tu models.py)
        context['total_proyectos'] = base_queryset.count()
        context['proyectos_activos'] = base_queryset.filter(estado='ejecucion').count()
        context['proyectos_pausados'] = base_queryset.filter(estado='pausado').count()
        context['proyectos_finalizados'] = base_queryset.filter(estado='finalizado').count()

        # [ARREGLO ADICIONAL] Esto llenará tu filtro de Supervisores

        context['supervisores'] = Usuario.objects.filter(
            activo=True,
            cuenta_aprobada=True,
            rol__codigo__in=['admin', 'gerente_general', 'gerente_proyecto']
        ).order_by('nombre_completo')
        
        # --- FIN DE CORRECCIÓN ---
        
        return context


class ProyectoDetalleView(LoginRequiredMixin, DetailView):
    """Vista para mostrar el detalle de un proyecto"""
    model = Proyecto
    template_name = 'proyectos/detalle.html'
    context_object_name = 'proyecto'
    
    def get_queryset(self):
        """Solo mostrar proyectos no eliminados"""
        return Proyecto.objects.filter(eliminado=False).select_related(
            'supervisor',
            'creado_por',
            'modificado_por'
        ).prefetch_related('trabajadores') # <-- Optimización

    def get_context_data(self, **kwargs):
        """Agrega datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        proyecto = self.get_object()
        
        # --- 2. CONTEXTO PARA TRABAJADORES ---
        context['trabajadores'] = proyecto.trabajadores.filter(eliminado=False)
        context['trabajadores_disponibles'] = Trabajador.objects.filter(
            Q(proyecto_asignado__isnull=True) | Q(proyecto_asignado=proyecto),
            eliminado=False,
            estado='activo'
        ).distinct()
        
        # --- 3. CONTEXTO PARA ASISTENCIAS ---
        
        # Asistencias recientes para la pestaña (ej: las últimas 15)
        context['asistencias_recientes'] = Asistencia.objects.filter(
            proyecto=proyecto,
            eliminado=False
        ).select_related('trabajador').order_by('-fecha', '-hora_entrada')[:15]
        
        # Conteo de asistencias de HOY para la tarjeta de Resumen
        context['asistencias_hoy'] = Asistencia.objects.filter(
            proyecto=proyecto, 
            fecha=timezone.now().date(), 
            estado='cerrado' # Contar solo los que marcaron salida
        ).count()
        
        # GREGAR: Contratistas asignados
        context['contratistas_asignados'] = proyecto.contratistas.filter(
            eliminado=False,
            activo=True
        ).order_by('apellido', 'nombre')
        # -----------------------------------------------

        # Información adicional
        context['puede_editar'] = proyecto.puede_ser_editado_por(self.request.user)
        context['puede_eliminar'] = proyecto.puede_ser_eliminado_por(self.request.user)
        
        # ===============================================
        # CORRECCIÓN: CONTRATISTAS BASADOS EN CONTRATOS DEL PROYECTO
        # ===============================================
        from apps.contratistas.models import ContratoProyecto, Contratista

        # Obtener contratos del proyecto y agrupar por contratista
        contratos_del_proyecto = ContratoProyecto.objects.filter(
            proyecto=proyecto,
            eliminado=False
        ).select_related('contratista').prefetch_related('avaluos')

        # Agrupar por contratista
        contratistas_dict = {}
        for contrato in contratos_del_proyecto:
            contratista_id = contrato.contratista_id
            if contratista_id not in contratistas_dict:
                contratistas_dict[contratista_id] = {
                    'contratista': contrato.contratista,
                    'contratos': [],
                    'total_contratos': 0,
                    'total_pagado': Decimal('0.00'),
                }
            contratistas_dict[contratista_id]['contratos'].append(contrato)
            contratistas_dict[contratista_id]['total_contratos'] += 1
            contratistas_dict[contratista_id]['total_pagado'] += contrato.total_pagado

        contratistas_con_contratos = list(contratistas_dict.values())
        context['contratistas_con_contratos'] = contratistas_con_contratos

        return context


class ProyectoCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_modulo = 'proyectos'
    permission_accion = 'crear'
    """Vista para crear un nuevo proyecto"""
    template_name = 'proyectos/crear.html'
    
    def get(self, request):
        """Muestra el formulario de creación"""
        supervisores = Usuario.objects.filter(
            activo=True,
            rol__codigo__in=['admin', 'gerente_general', 'contador']
        ).order_by('nombre_completo')
        
        # ✅ AGREGAR ESTO:
        from apps.contratistas.models import Contratista
        contratistas_disponibles = Contratista.objects.filter(
            eliminado=False,
            activo=True
        ).order_by('apellido', 'nombre')
        
        # Lista de trabajadores disponibles (sin proyecto asignado o activos)
        trabajadores_disponibles = Trabajador.objects.filter(
            eliminado=False,
            estado='activo'
        ).filter(
            Q(proyecto_asignado__isnull=True) | Q(proyecto_asignado__isnull=False)
        ).order_by('apellido', 'nombre')

        context = {
            'supervisores': supervisores,
            'contratistas_disponibles': contratistas_disponibles,
            'trabajadores_disponibles': trabajadores_disponibles,
            'departamentos': DEPARTAMENTOS,
        }
        return render(request, self.template_name, context)
        
    def post(self, request):
        """Procesa el formulario de creación"""
        try:
            # Crear el proyecto con los datos del POST
            proyecto = Proyecto()
            
            # Información básica (EXISTENTE - NO CAMBIAR)
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.estado = request.POST.get('estado')
            proyecto.tipo_proyecto = request.POST.get('tipo_proyecto')
            
            # Ubicación (EXISTENTE - NO CAMBIAR)
            proyecto.ubicacion = request.POST.get('ubicacion')
            proyecto.ubicacion_coordenadas = request.POST.get('ubicacion_coordenadas', '')
            # ===============================
            # NORMALIZACIÓN GEO AUTOMÁTICA
            # ===============================
            coords = proyecto.ubicacion_coordenadas

            if coords and ',' in coords:
                try:
                    lat_str, lon_str = coords.split(',')
                    proyecto.latitud = float(lat_str.strip())
                    proyecto.longitud = float(lon_str.strip())
                except Exception as e:
                    print(f"[GEO PARSE ERROR] {coords} -> {e}")

            proyecto.departamento = request.POST.get('departamento', '')
            proyecto.municipio = request.POST.get('municipio', '')
            # RADIO GEOVALLA
            proyecto.radio_geovalla = int(request.POST.get('radio_geovalla', proyecto.radio_geovalla))

            # Características (EXISTENTE - NO CAMBIAR)
            proyecto.tamano_proyecto = request.POST.get('tamano_proyecto', 0)
            proyecto.cantidad_unidades = request.POST.get('cantidad_unidades', 0)
            proyecto.tamano_promedio = request.POST.get('tamano_promedio', 0)
            
            # Fechas (EXISTENTE - NO CAMBIAR)
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin_estimada = request.POST.get('fecha_fin_estimada') or None
            proyecto.fecha_inicio_obra = request.POST.get('fecha_inicio_obra') or None
            proyecto.fecha_entrega_estimada = request.POST.get('fecha_entrega_estimada') or None
            proyecto.fecha_acta_inicio = request.POST.get('fecha_acta_inicio') or None
            proyecto.fecha_acta_terminacion = request.POST.get('fecha_acta_terminacion') or None
            proyecto.plazo_ejecucion_meses = request.POST.get('plazo_ejecucion_meses', 0)
            proyecto.fecha_avaluo = request.POST.get('fecha_avaluo') or None
            
            # Personal (EXISTENTE - NO CAMBIAR)
            supervisor_id = request.POST.get('supervisor')
            if supervisor_id:
                proyecto.supervisor = Usuario.objects.get(id=supervisor_id)
            # proyecto.personal_asignado = request.POST.get('personal_asignado', 0)
            # proyecto.contratistas_asignados = request.POST.get('contratistas_asignados', 0)
            
            # Porcentajes (EXISTENTE - NO CAMBIAR)
            proyecto.porcentaje_avance_general = request.POST.get('porcentaje_avance_general', 0)
            proyecto.porcentaje_asignacion_planilla = request.POST.get('porcentaje_asignacion_planilla', 0)
            
            # Presupuesto (EXISTENTE - NO CAMBIAR)
            proyecto.presupuesto_total = request.POST.get('presupuesto_total', 0)
            proyecto.presupuesto_mano_obra = request.POST.get('presupuesto_mano_obra', 0)
            proyecto.presupuesto_administrativo = request.POST.get('presupuesto_administrativo', 0)
            proyecto.gasto_mano_obra_real = request.POST.get('gasto_mano_obra_real', 0)
            proyecto.gasto_administrativo_real = request.POST.get('gasto_administrativo_real', 0)
            proyecto.anticipo = request.POST.get('anticipo', 0)
            proyecto.valor_avaluo_acumulado = request.POST.get('valor_avaluo_acumulado', 0)
            
            # ============================================================
            # ✨ HORARIOS INDIVIDUALES POR DÍA (FORMATO 12H)
            # ============================================================

            # LUNES
            proyecto.hora_inicio_lunes = request.POST.get('hora_inicio_lunes', '08:00 AM')
            proyecto.hora_fin_lunes = request.POST.get('hora_fin_lunes', '05:00 PM')

            # MARTES
            proyecto.hora_inicio_martes = request.POST.get('hora_inicio_martes', '08:00 AM')
            proyecto.hora_fin_martes = request.POST.get('hora_fin_martes', '05:00 PM')

            # MIÉRCOLES
            proyecto.hora_inicio_miercoles = request.POST.get('hora_inicio_miercoles', '08:00 AM')
            proyecto.hora_fin_miercoles = request.POST.get('hora_fin_miercoles', '05:00 PM')

            # JUEVES
            proyecto.hora_inicio_jueves = request.POST.get('hora_inicio_jueves', '08:00 AM')
            proyecto.hora_fin_jueves = request.POST.get('hora_fin_jueves', '05:00 PM')

            # VIERNES
            proyecto.hora_inicio_viernes = request.POST.get('hora_inicio_viernes', '08:00 AM')
            proyecto.hora_fin_viernes = request.POST.get('hora_fin_viernes', '02:00 PM')

            # SÁBADO
            proyecto.hora_inicio_sabado = request.POST.get('hora_inicio_sabado', '08:00 AM')
            proyecto.hora_fin_sabado = request.POST.get('hora_fin_sabado', '12:00 PM')

            # DOMINGO (opcional)
            proyecto.hora_inicio_domingo = request.POST.get('hora_inicio_domingo', '')
            proyecto.hora_fin_domingo = request.POST.get('hora_fin_domingo', '')

            # DESCANSO POR DÍA
            proyecto.descanso_lunes = request.POST.get('descanso_lunes', '1:00')
            proyecto.descanso_martes = request.POST.get('descanso_martes', '1:00')
            proyecto.descanso_miercoles = request.POST.get('descanso_miercoles', '1:00')
            proyecto.descanso_jueves = request.POST.get('descanso_jueves', '1:00')
            proyecto.descanso_viernes = request.POST.get('descanso_viernes', '1:00')
            proyecto.descanso_sabado = request.POST.get('descanso_sabado', '0:00')
            proyecto.descanso_domingo = request.POST.get('descanso_domingo', '0:00')
            
            # TOLERANCIAS
            proyecto.minutos_tolerancia_entrada = int(request.POST.get('minutos_tolerancia_entrada', 15))
            proyecto.minutos_tolerancia_salida = int(request.POST.get('minutos_tolerancia_salida', 10))

            # DÍAS LABORALES (checkboxes)
            dias_laborales = request.POST.getlist('dias_laborales')
            if dias_laborales:
                proyecto.dias_laborales = ','.join(dias_laborales)
            else:
                proyecto.dias_laborales = '1,2,3,4,5,6'  # Lunes a Sábado por defecto
            # ============================================================
            # ============================================================
            
            # Archivos (EXISTENTE - NO CAMBIAR)
            if 'archivo_contrato' in request.FILES:
                proyecto.archivo_contrato = request.FILES['archivo_contrato']
            if 'archivo_avaluo' in request.FILES:
                proyecto.archivo_avaluo = request.FILES['archivo_avaluo']
            if 'archivo_presupuesto' in request.FILES:
                proyecto.archivo_presupuesto = request.FILES['archivo_presupuesto']
            if 'imagen_proyecto' in request.FILES:
                proyecto.imagen_proyecto = request.FILES['imagen_proyecto']
            
            # Estado (EXISTENTE - NO CAMBIAR)
            proyecto.activo = 'activo' in request.POST or request.POST.get('activo') == 'on'
            
            # Auditoría (EXISTENTE - NO CAMBIAR)
            proyecto.creado_por = request.user
            proyecto.modificado_por = request.user
            
            proyecto.save()
            
            # 1. Procesar contratistas seleccionados
            contratistas_ids = request.POST.get('contratistas_ids', '')
            if contratistas_ids:
                try:
                    from apps.contratistas.models import Contratista
                    ids_list = [int(id.strip()) for id in contratistas_ids.split(',') if id.strip()]
                    
                    # ✅ NUEVO: Asignar contratistas al proyecto usando ManyToMany
                    contratistas = Contratista.objects.filter(id__in=ids_list)
                    proyecto.contratistas.set(contratistas)
                    
                    # Actualizar el contador
                    proyecto.contratistas_asignados = len(ids_list)
                    proyecto.save()
                except Exception as e:
                    print(f"Error al procesar contratistas: {e}")

            # 2. Procesar avalúos cargados
            avaluos_data = request.POST.get('avaluos_data', '[]')
            if avaluos_data and avaluos_data != '[]':
                try:
                    from apps.contratistas.models import AvaluoContratista, ContratoProyecto, Contratista
                    from apps.core.utils import get_tipo_cambio_actual
                    
                    avaluos_list = json.loads(avaluos_data)
                    
                    for avaluo_data in avaluos_list:
                        contratista_id = avaluo_data.get('contratista_id')
                        
                        if not contratista_id:
                            continue
                        
                        try:
                            contratista = Contratista.objects.get(id=contratista_id)
                            
                            # Buscar o crear un contrato para este contratista en este proyecto
                            contrato, created = ContratoProyecto.objects.get_or_create(
                                contratista=contratista,
                                proyecto=proyecto,
                                defaults={
                                    'descripcion': f'Contrato {contratista.nombre_completo} - {proyecto.nombre}',
                                    'actividades': avaluo_data.get('descripcion', 'Actividades del proyecto'),
                                    'valor_contrato': Decimal('0.00'),  # Se debe definir el valor del contrato
                                    'fecha_inicio': proyecto.fecha_inicio,
                                    'estado': 'en_proceso',
                                    'creado_por': request.user
                                }
                            )
                            
                            # Crear el avalúo solo si hay datos completos
                            periodo_inicio = avaluo_data.get('periodo_inicio')
                            periodo_fin = avaluo_data.get('periodo_fin')
                            porcentaje = avaluo_data.get('porcentaje_avance', 0)
                            
                            if periodo_inicio and periodo_fin and porcentaje:
                                AvaluoContratista.objects.create(
                                    contrato=contrato,
                                    periodo_inicio=periodo_inicio,
                                    periodo_fin=periodo_fin,
                                    porcentaje_avance=Decimal(str(porcentaje)),
                                    concepto=avaluo_data.get('descripcion', 'Avalúo de trabajo realizado'),
                                    monto_cordobas=Decimal('0.00'),  # Se calculará después según % y valor del contrato
                                    tipo_cambio=get_tipo_cambio_actual(),
                                    ingresado_por=request.user,
                                    estado='pendiente'
                                )
                                
                        except Contratista.DoesNotExist:
                            print(f"Contratista {contratista_id} no existe")
                            continue
                        except Exception as e:
                            print(f"Error al crear avalúo: {e}")
                            continue
                            
                except json.JSONDecodeError:
                    print("Error: JSON de avalúos inválido")
                except Exception as e:
                    print(f"Error al procesar avalúos: {e}")
            
            # 3. Procesar trabajadores asignados
            trabajadores_ids = request.POST.get('trabajadores_ids', '')
            if trabajadores_ids:
                try:
                    # Convertir string "1,2,3" a lista de enteros
                    ids_list = [int(id.strip()) for id in trabajadores_ids.split(',') if id.strip()]
                    
                    # Asignar proyecto a cada trabajador
                    trabajadores_a_asignar = Trabajador.objects.filter(id__in=ids_list)
                    
                    for trabajador in trabajadores_a_asignar:
                        # Si estaba en otro proyecto, crear historial de salida
                        if trabajador.proyecto_asignado and trabajador.proyecto_asignado != proyecto:
                            HistorialProyecto.objects.filter(
                                trabajador=trabajador,
                                proyecto=trabajador.proyecto_asignado,
                                fecha_salida__isnull=True
                            ).update(
                                fecha_salida=timezone.now().date(),
                                motivo=f'Transferido a {proyecto.nombre} por {request.user.nombre_completo}'
                            )
                        
                        # Asignar nuevo proyecto
                        trabajador.proyecto_asignado = proyecto
                        trabajador.save()
                        
                        # Crear historial de entrada
                        HistorialProyecto.objects.create(
                            trabajador=trabajador,
                            proyecto=proyecto,
                            fecha_asignacion=timezone.now().date(),
                            motivo=f'Asignado al crear proyecto por {request.user.nombre_completo}',
                            creado_por=request.user
                        )
                    
                    # Actualizar el campo personal_asignado
                    proyecto.personal_asignado = len(ids_list)
                    proyecto.save()
                    
                except Exception as e:
                    print(f"Error al procesar trabajadores: {e}")

            messages.success(
                request,
                f'✅ Proyecto "{proyecto.nombre}" creado exitosamente con horario {proyecto.get_horario_display()}.'
            )
            return redirect('proyectos_lista')
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al crear el proyecto: {str(e)}'
            )
            
            supervisores = Usuario.objects.filter(
                activo=True,
                rol__codigo__in=['admin', 'gerente_general', 'contador']
            ).order_by('nombre_completo')
            
            context = {
                'supervisores': supervisores,
                'departamentos': DEPARTAMENTOS,
            }
            return render(request, self.template_name, context)


class ProyectoEditarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para editar un proyecto existente"""
    permission_modulo = 'proyectos'
    permission_accion = 'editar'
    template_name = 'proyectos/editar.html'
    
    def get(self, request, pk):
        """Muestra el formulario de edición"""
        proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(
                request,
                '❌ No tienes permisos para editar este proyecto.'
            )
            return redirect('proyecto_detalle', pk=pk)
        
        supervisores = Usuario.objects.filter(
            activo=True,
            rol__codigo__in=['admin', 'gerente_general', 'contador']
        ).order_by('nombre_completo')

        # AGREGAR: Contratistas y avalúos

        # Obtener contratistas asignados al proyecto (desde la relación ManyToMany)
        contratistas_asignados = proyecto.contratistas.filter(
            eliminado=False,
            activo=True
        ).order_by('apellido', 'nombre')

        # ✅ Obtener contratos del proyecto
        contratistas_proyecto = ContratoProyecto.objects.filter(
            proyecto=proyecto
        ).select_related('contratista').order_by('contratista__apellido')

        # Obtener avalúos existentes
        avaluos_existentes = AvaluoContratista.objects.filter(
            contrato__proyecto=proyecto
        ).select_related('contrato__contratista').order_by('-fecha_ingreso')

        # Usuarios disponibles para asignar al proyecto
        from apps.admin_panel.models import Rol
        from apps.proyectos.models import UsuarioProyecto
        roles_con_asignacion = Rol.objects.filter(
            alcance_proyectos__in=['asignados', 'propio']
        )
        usuarios_disponibles = Usuario.objects.filter(
            activo=True,
            cuenta_aprobada=True,
            rol__in=roles_con_asignacion
        ).order_by('nombre_completo')

        usuarios_asignados_ids = list(UsuarioProyecto.objects.filter(
            proyecto=proyecto,
            activo=True
        ).values_list('usuario_id', flat=True))

        context = {
            'proyecto': proyecto,
            'supervisores': supervisores,
            'contratistas_asignados': contratistas_asignados,
            'contratistas_proyecto': contratistas_proyecto,
            'avaluos_existentes': avaluos_existentes,
            'departamentos': DEPARTAMENTOS,
            'usuarios_disponibles': usuarios_disponibles,     
            'usuarios_asignados_ids': usuarios_asignados_ids,  
        }

        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """Procesa el formulario de edición"""
        proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
        
        # Verificar permisos (EXISTENTE - NO CAMBIAR)
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(
                request,
                '❌ No tienes permisos para editar este proyecto.'
            )
            return redirect('proyecto_detalle', pk=pk)
        
        try:
            # Actualizar campos básicos (EXISTENTE - NO CAMBIAR)
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.estado = request.POST.get('estado')
            proyecto.tipo_proyecto = request.POST.get('tipo_proyecto')
            
            # Ubicación (EXISTENTE - NO CAMBIAR)
            proyecto.ubicacion = request.POST.get('ubicacion')
            proyecto.ubicacion_coordenadas = request.POST.get('ubicacion_coordenadas', '')
            proyecto.departamento = request.POST.get('departamento', '')
            proyecto.municipio = request.POST.get('municipio', '')
            # RADIO GEOVALLA
            proyecto.radio_geovalla = int(request.POST.get('radio_geovalla', proyecto.radio_geovalla))

            # Características (EXISTENTE - NO CAMBIAR)
            proyecto.tamano_proyecto = request.POST.get('tamano_proyecto', 0)
            proyecto.cantidad_unidades = request.POST.get('cantidad_unidades', 0)
            proyecto.tamano_promedio = request.POST.get('tamano_promedio', 0)
            
            # Fechas (EXISTENTE - NO CAMBIAR)
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin_estimada = request.POST.get('fecha_fin_estimada') or None
            proyecto.fecha_inicio_obra = request.POST.get('fecha_inicio_obra') or None
            proyecto.fecha_entrega_estimada = request.POST.get('fecha_entrega_estimada') or None
            proyecto.fecha_acta_inicio = request.POST.get('fecha_acta_inicio') or None
            proyecto.fecha_acta_terminacion = request.POST.get('fecha_acta_terminacion') or None
            proyecto.plazo_ejecucion_meses = request.POST.get('plazo_ejecucion_meses', 0)
            proyecto.fecha_avaluo = request.POST.get('fecha_avaluo') or None
            
            # Personal (EXISTENTE - NO CAMBIAR)
            supervisor_id = request.POST.get('supervisor')
            proyecto.supervisor = Usuario.objects.get(id=supervisor_id)
            proyecto.personal_asignado = request.POST.get('personal_asignado', 0)
            proyecto.contratistas_asignados = request.POST.get('contratistas_asignados', 0)
            
            # Guardar asignaciones de usuarios al proyecto
            from apps.proyectos.models import UsuarioProyecto
            usuarios_proyecto_ids = request.POST.getlist('usuarios_proyecto')
            UsuarioProyecto.objects.filter(proyecto=proyecto).update(activo=False)
            for uid in usuarios_proyecto_ids:
                UsuarioProyecto.objects.update_or_create(
                    usuario_id=uid,
                    proyecto=proyecto,
                    defaults={
                        'activo': True,
                        'asignado_por': request.user
                    }
                )
            # Actualizar contadores automáticamente
            proyecto.personal_asignado = proyecto.trabajadores.filter(eliminado=False).count()
            proyecto.contratistas_asignados = proyecto.contratistas.filter(eliminado=False, activo=True).count()
            proyecto.save()
            # Porcentajes (EXISTENTE - NO CAMBIAR)
            proyecto.porcentaje_avance_general = request.POST.get('porcentaje_avance_general', 0)
            proyecto.porcentaje_asignacion_planilla = request.POST.get('porcentaje_asignacion_planilla', 0)
            
            # Presupuesto (EXISTENTE - NO CAMBIAR)
            proyecto.presupuesto_total = request.POST.get('presupuesto_total', 0)
            proyecto.presupuesto_mano_obra = request.POST.get('presupuesto_mano_obra', 0)
            proyecto.presupuesto_administrativo = request.POST.get('presupuesto_administrativo', 0)
            proyecto.gasto_mano_obra_real = request.POST.get('gasto_mano_obra_real', 0)
            proyecto.gasto_administrativo_real = request.POST.get('gasto_administrativo_real', 0)
            proyecto.anticipo = request.POST.get('anticipo', 0)
            proyecto.valor_avaluo_acumulado = request.POST.get('valor_avaluo_acumulado', 0)
            
            # ============================================================
            # ✨ ACTUALIZAR HORARIOS INDIVIDUALES POR DÍA (FORMATO 12H)
            # ============================================================

            # LUNES
            if request.POST.get('hora_inicio_lunes'):
                proyecto.hora_inicio_lunes = request.POST.get('hora_inicio_lunes')
            if request.POST.get('hora_fin_lunes'):
                proyecto.hora_fin_lunes = request.POST.get('hora_fin_lunes')

            # MARTES
            if request.POST.get('hora_inicio_martes'):
                proyecto.hora_inicio_martes = request.POST.get('hora_inicio_martes')
            if request.POST.get('hora_fin_martes'):
                proyecto.hora_fin_martes = request.POST.get('hora_fin_martes')

            # MIÉRCOLES
            if request.POST.get('hora_inicio_miercoles'):
                proyecto.hora_inicio_miercoles = request.POST.get('hora_inicio_miercoles')
            if request.POST.get('hora_fin_miercoles'):
                proyecto.hora_fin_miercoles = request.POST.get('hora_fin_miercoles')

            # JUEVES
            if request.POST.get('hora_inicio_jueves'):
                proyecto.hora_inicio_jueves = request.POST.get('hora_inicio_jueves')
            if request.POST.get('hora_fin_jueves'):
                proyecto.hora_fin_jueves = request.POST.get('hora_fin_jueves')

            # VIERNES
            if request.POST.get('hora_inicio_viernes'):
                proyecto.hora_inicio_viernes = request.POST.get('hora_inicio_viernes')
            if request.POST.get('hora_fin_viernes'):
                proyecto.hora_fin_viernes = request.POST.get('hora_fin_viernes')

            # SÁBADO
            if request.POST.get('hora_inicio_sabado'):
                proyecto.hora_inicio_sabado = request.POST.get('hora_inicio_sabado')
            if request.POST.get('hora_fin_sabado'):
                proyecto.hora_fin_sabado = request.POST.get('hora_fin_sabado')

            # DOMINGO
            if request.POST.get('hora_inicio_domingo'):
                proyecto.hora_inicio_domingo = request.POST.get('hora_inicio_domingo')
            if request.POST.get('hora_fin_domingo'):
                proyecto.hora_fin_domingo = request.POST.get('hora_fin_domingo')

            # ============================================================
            # DESCANSO POR DÍA
            # ============================================================
            proyecto.descanso_lunes = request.POST.get('descanso_lunes', '1:00')
            proyecto.descanso_martes = request.POST.get('descanso_martes', '1:00')
            proyecto.descanso_miercoles = request.POST.get('descanso_miercoles', '1:00')
            proyecto.descanso_jueves = request.POST.get('descanso_jueves', '1:00')
            proyecto.descanso_viernes = request.POST.get('descanso_viernes', '1:00')
            proyecto.descanso_sabado = request.POST.get('descanso_sabado', '0:00')
            proyecto.descanso_domingo = request.POST.get('descanso_domingo', '0:00')
            
            # TOLERANCIAS
            if request.POST.get('minutos_tolerancia_entrada'):
                proyecto.minutos_tolerancia_entrada = int(request.POST.get('minutos_tolerancia_entrada'))
            if request.POST.get('minutos_tolerancia_salida'):
                proyecto.minutos_tolerancia_salida = int(request.POST.get('minutos_tolerancia_salida'))

            # DÍAS LABORALES
            dias_laborales = request.POST.getlist('dias_laborales')
            if dias_laborales:
                proyecto.dias_laborales = ','.join(dias_laborales)
            # ============================================================
            # ============================================================
            
            # Archivos (EXISTENTE - NO CAMBIAR)
            if 'archivo_contrato' in request.FILES:
                proyecto.archivo_contrato = request.FILES['archivo_contrato']
            if 'archivo_avaluo' in request.FILES:
                proyecto.archivo_avaluo = request.FILES['archivo_avaluo']
            if 'archivo_presupuesto' in request.FILES:
                proyecto.archivo_presupuesto = request.FILES['archivo_presupuesto']
            if 'imagen_proyecto' in request.FILES:
                proyecto.imagen_proyecto = request.FILES['imagen_proyecto']
            
            avaluos_data = request.POST.get('avaluos_data', '[]')
            if avaluos_data and avaluos_data != '[]':
                try:
                    avaluos_list = json.loads(avaluos_data)
                    
                    for avaluo_data in avaluos_list:
                        contratista_id = avaluo_data.get('contratista_id')
                        
                        if not contratista_id:
                            continue
                        
                        try:
                            # Buscar el contrato existente
                            contrato = ContratoProyecto.objects.get(
                                contratista_id=contratista_id,
                                proyecto=proyecto
                            )
                            
                            # Crear el avalúo
                            periodo_inicio = avaluo_data.get('periodo_inicio')
                            periodo_fin = avaluo_data.get('periodo_fin')
                            porcentaje = avaluo_data.get('porcentaje_avance', 0)
                            
                            if periodo_inicio and periodo_fin and porcentaje:
                                avaluo = AvaluoContratista.objects.create(
                                    contrato=contrato,
                                    periodo_inicio=periodo_inicio,
                                    periodo_fin=periodo_fin,
                                    porcentaje_avance=Decimal(str(porcentaje)),
                                    concepto=avaluo_data.get('descripcion', 'Avalúo de avance'),
                                    monto_cordobas=Decimal('0.00'),
                                    ingresado_por=request.user,
                                    estado='pendiente'
                                )
                                
                                # ✅ NUEVO: Procesar archivo si existe
                                archivo_key = f"avaluo_archivo_{avaluo_data.get('index', '')}"
                                if archivo_key in request.FILES:
                                    avaluo.archivo_soporte = request.FILES[archivo_key]
                                    avaluo.save()
                                
                        except ContratoProyecto.DoesNotExist:
                            print(f"Contrato no encontrado para contratista {contratista_id}")
                            continue
                        except Exception as e:
                            print(f"Error al crear avalúo: {e}")
                            continue
                            
                except json.JSONDecodeError:
                    print("Error: JSON de avalúos inválido")
                except Exception as e:
                    print(f"Error al procesar avalúos: {e}")

            # Estado (EXISTENTE - NO CAMBIAR)
            proyecto.activo = 'activo' in request.POST or request.POST.get('activo') == 'on'
            
            # Auditoría (EXISTENTE - NO CAMBIAR)
            proyecto.modificado_por = request.user
            
            proyecto.save()
            
            messages.success(
                request,
                f'✅ Proyecto "{proyecto.nombre}" actualizado exitosamente.'
            )
            return redirect('proyecto_detalle', pk=proyecto.pk)
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al actualizar el proyecto: {str(e)}'
            )
            
            supervisores = Usuario.objects.filter(
                activo=True,
                rol__codigo__in=['admin', 'gerente_general', 'contador']
            ).order_by('nombre_completo') 
            
            context = {
                'proyecto': proyecto,
                'supervisores': supervisores,
                'departamentos': DEPARTAMENTOS,
            }
            return render(request, self.template_name, context)



class ProyectoEliminarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para eliminar (soft delete) un proyecto"""
    permission_modulo = 'proyectos'
    permission_accion = 'eliminar'
    
    def post(self, request, pk):
        """Maneja la eliminación del proyecto"""
        try:
            proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
            
            # Verificar permisos - Solo administradores pueden eliminar
            if not proyecto.puede_ser_eliminado_por(request.user):
                messages.error(
                    request,
                    '❌ No tienes permisos para eliminar este proyecto.'
                )
                return redirect('proyecto_detalle', pk=pk)
            
            # Soft delete
            nombre_proyecto = proyecto.nombre
            proyecto.soft_delete(request.user)
            
            messages.success(
                request,
                f'✅ Proyecto "{nombre_proyecto}" eliminado exitosamente.'
            )
            return redirect('proyectos_lista')
            
        except Proyecto.DoesNotExist:
            messages.error(
                request,
                '❌ El proyecto no existe o ya fue eliminado.'
            )
            return redirect('proyectos_lista')
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al eliminar el proyecto: {str(e)}'
            )
            return redirect('proyecto_detalle', pk=pk)


class ProyectoRestaurarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para restaurar un proyecto eliminado"""
    permission_modulo = 'proyectos'
    permission_accion = 'editar'
    
    def post(self, request, pk):
        """Maneja la restauración del proyecto"""
        try:
            # Solo administradores pueden restaurar
            if not request.user.es_administrador():
                messages.error(
                    request,
                    '❌ No tienes permisos para restaurar proyectos.'
                )
                return redirect('proyectos_lista')
            
            proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=True)
            nombre_proyecto = proyecto.nombre
            proyecto.restaurar()
            
            messages.success(
                request,
                f'✅ Proyecto "{nombre_proyecto}" restaurado exitosamente.'
            )
            return redirect('proyecto_detalle', pk=pk)
            
        except Proyecto.DoesNotExist:
            messages.error(
                request,
                '❌ El proyecto no existe o no está eliminado.'
            )
            return redirect('proyectos_lista')
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al restaurar el proyecto: {str(e)}'
            )
            return redirect('proyectos_lista')


class ProyectosEliminadosView(LoginRequiredMixin, ListView):
    """Vista para listar proyectos eliminados (solo administradores)"""
    model = Proyecto
    template_name = 'proyectos/eliminados.html'
    context_object_name = 'proyectos'
    paginate_by = 12
    
    def dispatch(self, request, *args, **kwargs):
        """Verificar que solo administradores accedan"""
        if not request.user.es_administrador():
            messages.error(
                request,
                '❌ No tienes permisos para acceder a esta sección.'
            )
            return redirect('proyectos_lista')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Retorna solo proyectos eliminados"""
        queryset = Proyecto.objects.filter(eliminado=True).select_related(
            'supervisor',
            'eliminado_por'
        ).order_by('-fecha_eliminacion')
        
        # Filtro de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ubicacion__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Agrega datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        context['total_eliminados'] = Proyecto.objects.filter(eliminado=True).count()
        context['search_query'] = self.request.GET.get('search', '')
        return context


class ProyectoToggleActivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para activar/desactivar un proyecto"""
    permission_modulo = 'proyectos'
    permission_accion = 'editar'
    
    def post(self, request, pk):
        """Maneja el cambio de estado activo"""
        try:
            proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
            
            # Verificar permisos
            if not request.user.es_administrador():
                messages.error(
                    request,
                    '❌ No tienes permisos para cambiar el estado del proyecto.'
                )
                # [CAMBIO] Redirigir a la lista
                return redirect('proyectos_lista') 
            
            # [CAMBIO] Leer el estado enviado desde el formulario
            nuevo_estado = request.POST.get('estado')

            # Usamos los estados de tu models.py: 'ejecucion' y 'pausado'
            if nuevo_estado in ['ejecucion', 'pausado']:
                proyecto.estado = nuevo_estado
                proyecto.modificado_por = request.user
                proyecto.save()
                
                estado_str = "reactivado" if nuevo_estado == "ejecucion" else "pausado"
                messages.success(
                    request,
                    f'✅ Proyecto "{proyecto.nombre}" {estado_str} exitosamente.'
                )
            else:
                messages.error(request, '❌ Estado no válido proporcionado.')
            
            # [CAMBIO] Redirigir de vuelta a la lista de proyectos
            return redirect('proyectos_lista')
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al cambiar el estado: {str(e)}'
            )
            return redirect('proyectos_lista')
# ============================================
# [NUEVA VISTA] PARA MANEJAR EL MODAL
# ============================================
class ProyectoAsignarTrabajadoresView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para manejar la asignación de trabajadores desde el modal de detalle"""
    permission_modulo = 'proyectos'
    permission_accion = 'editar'
    
    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
        
        # Verificar permisos (solo admin o supervisor del proyecto)
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(request, '❌ No tienes permisos para asignar trabajadores a este proyecto.')
            return redirect('proyecto_detalle', pk=pk)

        try:
            # 1. Obtener la lista de IDs que se enviaron desde el formulario
            trabajadores_ids_enviados = set(request.POST.getlist('trabajadores'))
            
            # 2. Obtener la lista de IDs que ya están asignados a ESTE proyecto
            trabajadores_actuales_ids = set(
                proyecto.trabajadores.filter(eliminado=False).values_list('id', flat=True)
            )

            # 3. Convertir IDs de string a int
            trabajadores_ids_enviados_int = {int(id_str) for id_str in trabajadores_ids_enviados}

            # 4. Calcular diferencias
            ids_para_agregar = list(trabajadores_ids_enviados_int - trabajadores_actuales_ids)
            ids_para_quitar = list(trabajadores_actuales_ids - trabajadores_ids_enviados_int)
            
            # 5. Quitar asignación (poner proyecto_asignado = None)
            trabajadores_a_quitar = Trabajador.objects.filter(id__in=ids_para_quitar)
            
            for t in trabajadores_a_quitar:
                t.proyecto_asignado = None
                t.save()
                # Opcional: Registrar salida en historial
                HistorialProyecto.objects.filter(
                    trabajador=t,
                    proyecto=proyecto,
                    fecha_salida__isnull=True
                ).update(
                    fecha_salida=timezone.now().date(),
                    motivo=f'Desasignado (modal) por {request.user.nombre_completo}'
                )

            # 6. Poner/actualizar asignación
            trabajadores_a_agregar = Trabajador.objects.filter(id__in=ids_para_agregar)
            
            for t in trabajadores_a_agregar:
                proyecto_anterior = t.proyecto_asignado
                
                # Si estaba en otro proyecto, registrar salida
                if proyecto_anterior and proyecto_anterior != proyecto:
                    HistorialProyecto.objects.filter(
                        trabajador=t,
                        proyecto=proyecto_anterior,
                        fecha_salida__isnull=True
                    ).update(
                        fecha_salida=timezone.now().date(),
                        motivo=f'Transferido a {proyecto.nombre} por {request.user.nombre_completo}'
                    )
                
                # Asignar nuevo proyecto
                t.proyecto_asignado = proyecto
                t.save()
                
                # Crear nuevo historial de entrada
                HistorialProyecto.objects.create(
                    trabajador=t,
                    proyecto=proyecto,
                    fecha_asignacion=timezone.now().date(),
                    motivo=f'Asignado (modal) por {request.user.nombre_completo}',
                    creado_por=request.user
                )
            
            messages.success(
                request,
                f'✅ Asignación actualizada: {len(ids_para_agregar)} agregados, {len(ids_para_quitar)} quitados.'
            )
            
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar trabajadores: {str(e)}')

        return redirect('proyecto_detalle', pk=pk)

# ============================================
# API VIEWS (Para tu app móvil)
# ============================================
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProyectoSerializer, MisProyectosSerializer


class ProyectoViewSet(viewsets.ModelViewSet):
    """ViewSet para la API REST de proyectos"""
    queryset = Proyecto.objects.filter(eliminado=False)
    serializer_class = ProyectoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar proyectos según el usuario"""
        user = self.request.user
        if user.es_administrador():
            return Proyecto.objects.filter(eliminado=False)
        return Proyecto.objects.filter(
            supervisor=user,
            eliminado=False
        )
    
    def perform_create(self, serializer):
        """Registrar auditoría al crear"""
        serializer.save(
            creado_por=self.request.user,
            modificado_por=self.request.user
        )
    
    def perform_update(self, serializer):
        """Registrar auditoría al actualizar"""
        serializer.save(modificado_por=self.request.user)

    # ============================================================
    # ✅ NUEVO ENDPOINT: MIS PROYECTOS
    # ============================================================
    @action(detail=False, methods=['get'], url_path='mis-proyectos')
    def mis_proyectos(self, request):
        """
        Endpoint específico para obtener los proyectos del supervisor logueado
        
        GET /api/proyectos/mis-proyectos/
        
        Returns:
            - Si es supervisor: Solo sus proyectos asignados
            - Si es administrador: Todos los proyectos
            
        Response:
            {
                "count": 2,
                "proyectos": [...]
            }
        """
        user = request.user
        
        # Filtrar proyectos según el rol
        if user.es_administrador():
            proyectos = Proyecto.objects.filter(
                eliminado=False,
                ).select_related('supervisor').order_by('-fecha_creacion')
        else:
            # Solo proyectos donde es supervisor
            proyectos = Proyecto.objects.filter(
                supervisor=user,
                eliminado=False,
            ).select_related('supervisor').order_by('-fecha_creacion')
        
        # Serializar
        serializer = MisProyectosSerializer(proyectos, many=True)
        
        return Response({
            'count': proyectos.count(),
            'proyectos': serializer.data,
            'usuario': {
                'id': user.id,
                'nombre': user.nombre_completo,
                'rol': user.rol.nombre if user.rol else 'Sin rol'
            }
        }, status=status.HTTP_200_OK)

# ============================================================
# VISTA AJAX PARA CREAR CONTRATISTA DESDE FORMULARIO DE PROYECTO
# ============================================================
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

@method_decorator(csrf_exempt, name='dispatch')
class ContratistaCrearAjaxView(LoginRequiredMixin, View):
    """
    Vista AJAX para crear un contratista rápidamente desde el modal
    del formulario de crear proyecto.
    """
    
    def post(self, request):
        try:
            # El JavaScript envía JSON en el body
            data = json.loads(request.body)
            
            # Validar campos requeridos
            campos_requeridos = ['nombre', 'apellido', 'numero_cedula', 'direccion']
            for campo in campos_requeridos:
                if not data.get(campo):
                    return JsonResponse({
                        'success': False,
                        'error': f'El campo {campo} es requerido'
                    }, status=400)
            
            # Verificar que la cédula no exista
            if Contratista.objects.filter(numero_cedula=data.get('numero_cedula')).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Ya existe un contratista con esa cédula'
                }, status=400)
            
            # Crear el contratista
            contratista = Contratista.objects.create(
                nombre=data.get('nombre'),
                apellido=data.get('apellido'),
                numero_cedula=data.get('numero_cedula'),
                telefono=data.get('telefono', ''),
                direccion=data.get('direccion'),
                departamento=data.get('departamento', ''),
                municipio=data.get('municipio', ''),
                banco=data.get('banco', ''),
                numero_cuenta=data.get('numero_cuenta', ''),
                tipo_cuenta=data.get('tipo_cuenta', ''),
                moneda_cuenta=data.get('moneda_cuenta', 'cordobas'),
                creado_por=request.user
            )
            
            # Retornar los datos del contratista creado
            return JsonResponse({
                'success': True,
                'contratista': {
                    'id': contratista.id,
                    'nombre_completo': contratista.nombre_completo,
                    'cedula': contratista.numero_cedula
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Formato JSON inválido'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        