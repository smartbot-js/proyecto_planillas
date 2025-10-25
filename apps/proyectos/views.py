"""
Views para la aplicación de proyectos
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.utils import timezone

from .models import Proyecto
from .serializers import (
    ProyectoSerializer,
    ProyectoCreateSerializer,
    ProyectoUpdateSerializer,
    ProyectoListSerializer,
    ProyectoDetalleSerializer,
)
from apps.usuarios.models import Usuario


# ========================================
# VISTAS API REST (para la app móvil)
# ========================================

class ProyectoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD de proyectos (API)
    """
    queryset = Proyecto.objects.select_related('supervisor').all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'list':
            return ProyectoListSerializer
        elif self.action == 'retrieve':
            return ProyectoDetalleSerializer
        elif self.action == 'create':
            return ProyectoCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProyectoUpdateSerializer
        return ProyectoSerializer
    
    def get_queryset(self):
        """Filtrar queryset según rol del usuario y parámetros"""
        user = self.request.user
        queryset = Proyecto.objects.select_related('supervisor').all()
        
        # Si es supervisor, solo ve sus proyectos
        if user.es_supervisor():
            queryset = queryset.filter(supervisor=user)
        
        # Filtros opcionales
        estado = self.request.query_params.get('estado', None)
        supervisor_id = self.request.query_params.get('supervisor', None)
        search = self.request.query_params.get('search', None)
        activos = self.request.query_params.get('activos', None)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if supervisor_id:
            queryset = queryset.filter(supervisor_id=supervisor_id)
        
        if activos == 'true':
            queryset = queryset.filter(estado=Proyecto.Estado.ACTIVO)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search) |
                Q(ubicacion__icontains=search)
            )
        
        return queryset.order_by('-fecha_creacion')
    
    def perform_create(self, serializer):
        """Crear proyecto"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """Activar un proyecto"""
        proyecto = self.get_object()
        proyecto.activar()
        serializer = self.get_serializer(proyecto)
        return Response({
            'message': 'Proyecto activado exitosamente',
            'proyecto': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def pausar(self, request, pk=None):
        """Pausar un proyecto"""
        proyecto = self.get_object()
        proyecto.pausar()
        serializer = self.get_serializer(proyecto)
        return Response({
            'message': 'Proyecto pausado exitosamente',
            'proyecto': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        """Finalizar un proyecto"""
        proyecto = self.get_object()
        proyecto.finalizar()
        serializer = self.get_serializer(proyecto)
        return Response({
            'message': 'Proyecto finalizado exitosamente',
            'proyecto': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar un proyecto"""
        proyecto = self.get_object()
        proyecto.cancelar()
        serializer = self.get_serializer(proyecto)
        return Response({
            'message': 'Proyecto cancelado',
            'proyecto': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Listar solo proyectos activos"""
        proyectos = self.get_queryset().filter(estado=Proyecto.Estado.ACTIVO)
        serializer = ProyectoListSerializer(proyectos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def mis_proyectos(self, request):
        """Listar proyectos del supervisor actual"""
        proyectos = Proyecto.objects.filter(supervisor=request.user)
        serializer = ProyectoListSerializer(proyectos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """Obtener estadísticas del proyecto"""
        proyecto = self.get_object()
        
        # Aquí podrías agregar más estadísticas cuando tengas
        # trabajadores, asistencias, etc.
        
        stats = {
            'presupuesto_total': float(proyecto.presupuesto),
            'presupuesto_gastado': float(proyecto.presupuesto_gastado),
            'presupuesto_disponible': float(proyecto.presupuesto_disponible()),
            'porcentaje_gastado': proyecto.porcentaje_gastado(),
            'dias_transcurridos': proyecto.dias_transcurridos(),
            'dias_restantes': proyecto.dias_restantes(),
            'estado': proyecto.estado,
        }
        
        return Response(stats)


# ========================================
# VISTAS DE TEMPLATES (para la web)
# ========================================

@method_decorator(login_required(login_url='login'), name='dispatch')
class ProyectoListView(View):
    """Vista para listar proyectos"""
    template_name = 'proyectos/lista.html'
    
    def get(self, request):
        user = request.user
        
        # Filtrar según rol
        if user.es_supervisor():
            proyectos = Proyecto.objects.filter(supervisor=user)
        else:
            proyectos = Proyecto.objects.all()
        
        # Filtros adicionales
        estado = request.GET.get('estado', '')
        if estado:
            proyectos = proyectos.filter(estado=estado)
        
        search = request.GET.get('search', '')
        if search:
            proyectos = proyectos.filter(
                Q(nombre__icontains=search) |
                Q(ubicacion__icontains=search)
            )
        
        proyectos = proyectos.select_related('supervisor').order_by('-fecha_creacion')
        
        context = {
            'proyectos': proyectos,
            'estados': Proyecto.Estado.choices,
            'estado_actual': estado,
            'search': search,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required(login_url='login'), name='dispatch')
class ProyectoCreateView(View):
    """Vista para crear proyecto"""
    template_name = 'proyectos/crear.html'
    
    def get(self, request):
        # Solo administradores pueden crear proyectos
        if not request.user.es_administrador():
            messages.error(request, 'No tienes permisos para crear proyectos.')
            return redirect('proyectos_lista')
        
        # Obtener supervisores disponibles
        supervisores = Usuario.objects.filter(
            Q(rol='administrador') | Q(rol='supervisor'),
            activo=True
        )
        
        context = {
            'supervisores': supervisores,
            'estados': Proyecto.Estado.choices,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not request.user.es_administrador():
            messages.error(request, 'No tienes permisos para crear proyectos.')
            return redirect('proyectos_lista')
        
        try:
            proyecto = Proyecto.objects.create(
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                ubicacion=request.POST.get('ubicacion'),
                fecha_inicio=request.POST.get('fecha_inicio'),
                fecha_fin_estimada=request.POST.get('fecha_fin_estimada') or None,
                supervisor_id=request.POST.get('supervisor'),
                presupuesto=request.POST.get('presupuesto'),
                estado=request.POST.get('estado', 'activo'),
            )
            messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente.')
            return redirect('proyecto_detalle', pk=proyecto.id)
        except Exception as e:
            messages.error(request, f'Error al crear proyecto: {str(e)}')
            return redirect('proyecto_crear')


@method_decorator(login_required(login_url='login'), name='dispatch')
class ProyectoDetalleView(View):
    """Vista para ver detalle del proyecto"""
    template_name = 'proyectos/detalle.html'
    
    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        
        # Verificar permisos
        if request.user.es_supervisor() and proyecto.supervisor != request.user:
            messages.error(request, 'No tienes permisos para ver este proyecto.')
            return redirect('proyectos_lista')
        
        context = {
            'proyecto': proyecto,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required(login_url='login'), name='dispatch')
class ProyectoEditarView(View):
    """Vista para editar proyecto"""
    template_name = 'proyectos/editar.html'
    
    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        
        # Verificar permisos
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(request, 'No tienes permisos para editar este proyecto.')
            return redirect('proyecto_detalle', pk=pk)
        
        supervisores = Usuario.objects.filter(
            Q(rol='administrador') | Q(rol='supervisor'),
            activo=True
        )
        
        context = {
            'proyecto': proyecto,
            'supervisores': supervisores,
            'estados': Proyecto.Estado.choices,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        
        if not proyecto.puede_ser_editado_por(request.user):
            messages.error(request, 'No tienes permisos para editar este proyecto.')
            return redirect('proyecto_detalle', pk=pk)
        
        try:
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.ubicacion = request.POST.get('ubicacion')
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin_estimada = request.POST.get('fecha_fin_estimada') or None
            proyecto.fecha_fin_real = request.POST.get('fecha_fin_real') or None
            proyecto.supervisor_id = request.POST.get('supervisor')
            proyecto.presupuesto = request.POST.get('presupuesto')
            proyecto.presupuesto_gastado = request.POST.get('presupuesto_gastado', 0)
            proyecto.estado = request.POST.get('estado')
            proyecto.save()
            
            messages.success(request, 'Proyecto actualizado exitosamente.')
            return redirect('proyecto_detalle', pk=proyecto.id)
        except Exception as e:
            messages.error(request, f'Error al actualizar proyecto: {str(e)}')
            return redirect('proyecto_editar', pk=pk)


@method_decorator(login_required(login_url='login'), name='dispatch')
class ProyectoEliminarView(View):
    """Vista para eliminar/cancelar proyecto"""
    
    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        
        if not request.user.es_administrador():
            messages.error(request, 'No tienes permisos para eliminar proyectos.')
            return redirect('proyecto_detalle', pk=pk)
        
        nombre = proyecto.nombre
        proyecto.cancelar()
        
        messages.success(request, f'Proyecto "{nombre}" cancelado exitosamente.')
        return redirect('proyectos_lista')
    
    