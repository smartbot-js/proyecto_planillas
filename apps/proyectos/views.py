from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Proyecto
from apps.usuarios.models import Usuario


class ProyectoListView(LoginRequiredMixin, ListView):
    """Vista para listar todos los proyectos"""
    model = Proyecto
    template_name = 'proyectos/lista.html'
    context_object_name = 'proyectos'
    paginate_by = 12
    
    def get_queryset(self):
        """Retorna el queryset filtrado de proyectos (excluye eliminados)"""
        queryset = Proyecto.objects.filter(eliminado=False).select_related('supervisor')
        
        # Filtro de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ubicacion__icontains=search) |
                Q(supervisor__nombre_completo__icontains=search)
            )
        
        # Filtro de estado
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
        
        # Estadísticas
        context['total_proyectos'] = Proyecto.objects.filter(eliminado=False).count()
        context['proyectos_activos'] = Proyecto.objects.filter(
            activo=True, 
            eliminado=False
        ).count()
        context['proyectos_en_ejecucion'] = Proyecto.objects.filter(
            estado='ejecucion',
            eliminado=False
        ).count()
        
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
        )
    
    def get_context_data(self, **kwargs):
        """Agrega datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        proyecto = self.get_object()
        
        # Información adicional
        context['puede_editar'] = proyecto.puede_ser_editado_por(self.request.user)
        context['puede_eliminar'] = proyecto.puede_ser_eliminado_por(self.request.user)
        
        return context


class ProyectoCreateView(LoginRequiredMixin, View):
    """Vista para crear un nuevo proyecto"""
    template_name = 'proyectos/crear.html'
    
    def get(self, request):
        """Muestra el formulario de creación"""
        supervisores = Usuario.objects.filter(
            activo=True,
            rol__in=['administrador', 'supervisor']
        ).order_by('nombre_completo')  # ← CAMBIO AQUÍ
        
        context = {
            'supervisores': supervisores,
        }
        return render(request, self.template_name, context)
        
    def post(self, request):
        """Procesa el formulario de creación"""
        try:
            # Crear el proyecto con los datos del POST
            proyecto = Proyecto()
            
            # Información básica
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.estado = request.POST.get('estado')
            proyecto.tipo_proyecto = request.POST.get('tipo_proyecto')
            
            # Ubicación
            proyecto.ubicacion = request.POST.get('ubicacion')
            proyecto.ubicacion_coordenadas = request.POST.get('ubicacion_coordenadas', '')
            proyecto.departamento = request.POST.get('departamento', '')
            proyecto.municipio = request.POST.get('municipio', '')
            
            # Características
            proyecto.tamano_proyecto = request.POST.get('tamano_proyecto', 0)
            proyecto.cantidad_unidades = request.POST.get('cantidad_unidades', 0)
            proyecto.tamano_promedio = request.POST.get('tamano_promedio', 0)
            
            # Fechas
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin_estimada = request.POST.get('fecha_fin_estimada') or None
            proyecto.fecha_avaluo = request.POST.get('fecha_avaluo') or None
            
            # Personal
            supervisor_id = request.POST.get('supervisor')
            proyecto.supervisor = Usuario.objects.get(id=supervisor_id)
            proyecto.personal_asignado = request.POST.get('personal_asignado', 0)
            proyecto.contratistas_asignados = request.POST.get('contratistas_asignados', 0)
            
            # Porcentajes
            proyecto.porcentaje_avance_general = request.POST.get('porcentaje_avance_general', 0)
            proyecto.porcentaje_asignacion_planilla = request.POST.get('porcentaje_asignacion_planilla', 0)
            
            # Presupuesto
            proyecto.presupuesto_total = request.POST.get('presupuesto_total', 0)
            proyecto.presupuesto_mano_obra = request.POST.get('presupuesto_mano_obra', 0)
            proyecto.presupuesto_administrativo = request.POST.get('presupuesto_administrativo', 0)
            proyecto.gasto_mano_obra_real = request.POST.get('gasto_mano_obra_real', 0)
            proyecto.gasto_administrativo_real = request.POST.get('gasto_administrativo_real', 0)
            proyecto.anticipo = request.POST.get('anticipo', 0)
            proyecto.valor_avaluo_acumulado = request.POST.get('valor_avaluo_acumulado', 0)
            
            # Archivos
            if 'archivo_contrato' in request.FILES:
                proyecto.archivo_contrato = request.FILES['archivo_contrato']
            if 'archivo_avaluo' in request.FILES:
                proyecto.archivo_avaluo = request.FILES['archivo_avaluo']
            if 'archivo_presupuesto' in request.FILES:
                proyecto.archivo_presupuesto = request.FILES['archivo_presupuesto']
            if 'imagen_proyecto' in request.FILES:
                proyecto.imagen_proyecto = request.FILES['imagen_proyecto']
            
            # Estado
            proyecto.activo = 'activo' in request.POST or request.POST.get('activo') == 'on'
            
            # 🆕 AUDITORÍA: Registrar quién creó el proyecto
            proyecto.creado_por = request.user
            proyecto.modificado_por = request.user
            
            proyecto.save()
            
            messages.success(
                request,
                f'✅ Proyecto "{proyecto.nombre}" creado exitosamente.'
            )
            return redirect('proyectos_lista')
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al crear el proyecto: {str(e)}'
            )
            
            supervisores = Usuario.objects.filter(
                activo=True,
                rol__in=['administrador', 'supervisor']
            ).order_by('nombre_completo')
            
            context = {
                'supervisores': supervisores,
            }
            return render(request, self.template_name, context)


class ProyectoEditarView(LoginRequiredMixin, View):
    """Vista para editar un proyecto existente"""
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
            rol__in=['administrador', 'supervisor']
        ).order_by('nombre_completo') 
        
        context = {
            'proyecto': proyecto,
            'supervisores': supervisores,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """Procesa el formulario de edición"""
        proyecto = get_object_or_404(Proyecto, pk=pk, eliminado=False)
        
        # Verificar permisos
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(
                request,
                '❌ No tienes permisos para editar este proyecto.'
            )
            return redirect('proyecto_detalle', pk=pk)
        
        try:
            # Actualizar campos
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.estado = request.POST.get('estado')
            proyecto.tipo_proyecto = request.POST.get('tipo_proyecto')
            
            # Ubicación
            proyecto.ubicacion = request.POST.get('ubicacion')
            proyecto.ubicacion_coordenadas = request.POST.get('ubicacion_coordenadas', '')
            proyecto.departamento = request.POST.get('departamento', '')
            proyecto.municipio = request.POST.get('municipio', '')
            
            # Características
            proyecto.tamano_proyecto = request.POST.get('tamano_proyecto', 0)
            proyecto.cantidad_unidades = request.POST.get('cantidad_unidades', 0)
            proyecto.tamano_promedio = request.POST.get('tamano_promedio', 0)
            
            # Fechas
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin_estimada = request.POST.get('fecha_fin_estimada') or None
            proyecto.fecha_avaluo = request.POST.get('fecha_avaluo') or None
            
            # Personal
            supervisor_id = request.POST.get('supervisor')
            proyecto.supervisor = Usuario.objects.get(id=supervisor_id)
            proyecto.personal_asignado = request.POST.get('personal_asignado', 0)
            proyecto.contratistas_asignados = request.POST.get('contratistas_asignados', 0)
            
            # Porcentajes
            proyecto.porcentaje_avance_general = request.POST.get('porcentaje_avance_general', 0)
            proyecto.porcentaje_asignacion_planilla = request.POST.get('porcentaje_asignacion_planilla', 0)
            
            # Presupuesto
            proyecto.presupuesto_total = request.POST.get('presupuesto_total', 0)
            proyecto.presupuesto_mano_obra = request.POST.get('presupuesto_mano_obra', 0)
            proyecto.presupuesto_administrativo = request.POST.get('presupuesto_administrativo', 0)
            proyecto.gasto_mano_obra_real = request.POST.get('gasto_mano_obra_real', 0)
            proyecto.gasto_administrativo_real = request.POST.get('gasto_administrativo_real', 0)
            proyecto.anticipo = request.POST.get('anticipo', 0)
            proyecto.valor_avaluo_acumulado = request.POST.get('valor_avaluo_acumulado', 0)
            
            # Archivos (solo si se suben nuevos)
            if 'archivo_contrato' in request.FILES:
                proyecto.archivo_contrato = request.FILES['archivo_contrato']
            if 'archivo_avaluo' in request.FILES:
                proyecto.archivo_avaluo = request.FILES['archivo_avaluo']
            if 'archivo_presupuesto' in request.FILES:
                proyecto.archivo_presupuesto = request.FILES['archivo_presupuesto']
            if 'imagen_proyecto' in request.FILES:
                proyecto.imagen_proyecto = request.FILES['imagen_proyecto']
            
            # Estado
            proyecto.activo = 'activo' in request.POST or request.POST.get('activo') == 'on'
            
            # 🆕 AUDITORÍA: Registrar quién modificó el proyecto
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
                rol__in=['administrador', 'supervisor']
            ).order_by('nombre_completo') 
            
            context = {
                'proyecto': proyecto,
                'supervisores': supervisores,
            }
            return render(request, self.template_name, context)


class ProyectoEliminarView(LoginRequiredMixin, View):
    """Vista para eliminar (soft delete) un proyecto"""
    
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


class ProyectoRestaurarView(LoginRequiredMixin, View):
    """Vista para restaurar un proyecto eliminado"""
    
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


class ProyectoToggleActivoView(LoginRequiredMixin, View):
    """Vista para activar/desactivar un proyecto"""
    
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
                return redirect('proyecto_detalle', pk=pk)
            
            # Cambiar estado
            proyecto.activo = not proyecto.activo
            proyecto.modificado_por = request.user
            proyecto.save()
            
            estado = "activado" if proyecto.activo else "desactivado"
            messages.success(
                request,
                f'✅ Proyecto "{proyecto.nombre}" {estado} exitosamente.'
            )
            return redirect('proyecto_detalle', pk=pk)
            
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al cambiar el estado: {str(e)}'
            )
            return redirect('proyectos_lista')


# ============================================
# API VIEWS (Para tu app móvil)
# ============================================
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import ProyectoSerializer


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