from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.utils import timezone

from .models import Rol
from .permissions import SuperAdminRequiredMixin
from .forms import RolForm, AsignarRolForm
from apps.usuarios.models import Usuario
from apps.proyectos.models import Proyecto, UsuarioProyecto

# ============================================
# GESTIÓN DE USUARIOS
# ============================================

class UsuariosListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """Lista de usuarios del sistema"""
    model = Usuario
    template_name = 'admin_panel/usuarios/lista.html'
    context_object_name = 'usuarios'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Usuario.objects.select_related('rol').prefetch_related(
            'proyectos_asignados__proyecto'
            ).order_by('-date_joined')
        
        buscar = self.request.GET.get('buscar', '').strip()
        if buscar:
            queryset = queryset.filter(
                Q(username__icontains=buscar) |
                Q(first_name__icontains=buscar) |
                Q(last_name__icontains=buscar) |
                Q(email__icontains=buscar)
            )
        
        estado = self.request.GET.get('estado', '')
        if estado == 'pendientes':
            queryset = queryset.filter(cuenta_aprobada=False, is_active=True)
        elif estado == 'activos':
            queryset = queryset.filter(is_active=True, cuenta_aprobada=True)
        elif estado == 'inactivos':
            queryset = queryset.filter(is_active=False)
        
        rol_id = self.request.GET.get('rol', '')
        if rol_id:
            queryset = queryset.filter(rol_id=rol_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Rol.objects.filter(activo=True).order_by('nombre')
        context['pendientes_count'] = Usuario.objects.filter(cuenta_aprobada=False, is_active=True).count()
        return context

class AprobarCuentaView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """Aprobar cuenta de usuario"""
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        
        if usuario.cuenta_aprobada:
            messages.warning(request, f'La cuenta de {usuario.get_full_name()} ya estaba aprobada')
        else:
            usuario.cuenta_aprobada = True
            usuario.aprobada_por = request.user
            usuario.fecha_aprobacion = timezone.now()
            usuario.save()
            messages.success(request, f'Cuenta de {usuario.get_full_name()} aprobada exitosamente')
        
        return redirect('admin_panel:usuarios_lista')

class CambiarEstadoUsuarioView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """Activar/Desactivar usuario"""
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        
        if usuario.id == request.user.id:
            messages.error(request, 'No puedes desactivar tu propia cuenta')
            return redirect('admin_panel:usuarios_lista')
        
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        estado = 'activado' if usuario.is_active else 'desactivado'
        messages.success(request, f'Usuario {usuario.get_full_name()} {estado} exitosamente')
        
        return redirect('admin_panel:usuarios_lista')

class AsignarRolView(LoginRequiredMixin, SuperAdminRequiredMixin, UpdateView):
    """Asignar rol a usuario"""
    model = Usuario
    form_class = AsignarRolForm
    template_name = 'admin_panel/usuarios/asignar_rol.html'
    success_url = reverse_lazy('admin_panel:usuarios_lista')
    
    def form_valid(self, form):
        messages.success(self.request, f'Rol asignado a {self.object.get_full_name()} exitosamente')
        return super().form_valid(form)

class AsignarProyectosUsuarioView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """Asignar proyectos a un usuario"""
    template_name = 'admin_panel/usuarios/asignar_proyectos.html'
    
    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        todos_proyectos = Proyecto.objects.filter(eliminado=False).order_by('nombre')
        asignados = UsuarioProyecto.objects.filter(
            usuario=usuario, activo=True
        ).values_list('proyecto_id', flat=True)
        
        return render(request, self.template_name, {
            'usuario': usuario,
            'todos_proyectos': todos_proyectos,
            'asignados': list(asignados),
        })
    
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        proyectos_ids = request.POST.getlist('proyectos')
        
        # Desactivar asignaciones anteriores
        UsuarioProyecto.objects.filter(usuario=usuario).update(activo=False)
        
        # Crear nuevas asignaciones
        for proyecto_id in proyectos_ids:
            UsuarioProyecto.objects.update_or_create(
                usuario=usuario,
                proyecto_id=proyecto_id,
                defaults={
                    'activo': True,
                    'asignado_por': request.user
                }
            )
        
        messages.success(request, f'Proyectos asignados a {usuario.nombre_completo}')
        return redirect('admin_panel:usuarios_lista')

# ============================================
# GESTIÓN DE ROLES
# ============================================

class RolesListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """Lista de roles del sistema"""
    model = Rol
    template_name = 'admin_panel/roles/lista.html'
    context_object_name = 'roles'
    
    def get_queryset(self):
        queryset = Rol.objects.annotate(
            num_usuarios=Count('usuarios')
        ).order_by('-es_sistema', 'nombre')
        
        buscar = self.request.GET.get('buscar', '').strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar) |
                Q(descripcion__icontains=buscar)
            )
        
        return queryset

class RolCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, CreateView):
    """Crear nuevo rol"""
    model = Rol
    form_class = RolForm
    template_name = 'admin_panel/roles/crear_editar.html'
    success_url = reverse_lazy('admin_panel:roles_lista')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, f'Rol "{form.instance.nombre}" creado exitosamente')
        return super().form_valid(form)

class RolUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, UpdateView):
    """Editar rol existente"""
    model = Rol
    form_class = RolForm
    template_name = 'admin_panel/roles/crear_editar.html'
    success_url = reverse_lazy('admin_panel:roles_lista')
    
    def get_queryset(self):
        # Permitir editar roles de sistema también
        return Rol.objects.all()
    
    def form_valid(self, form):
        # Proteger código de roles de sistema
        if form.instance.es_sistema:
            rol_original = Rol.objects.get(pk=form.instance.pk)
            form.instance.codigo = rol_original.codigo
        
        messages.success(self.request, f'Rol "{form.instance.nombre}" actualizado exitosamente')
        return super().form_valid(form)

class RolDeleteView(LoginRequiredMixin, SuperAdminRequiredMixin, DeleteView):
    """Eliminar rol (soft delete)"""
    model = Rol
    success_url = reverse_lazy('admin_panel:roles_lista')
    
    def get_queryset(self):
        return Rol.objects.filter(es_sistema=False)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if self.object.usuarios.exists():
            messages.error(request, f'No se puede eliminar el rol "{self.object.nombre}" porque tiene usuarios asignados')
            return redirect('admin_panel:roles_lista')
        
        self.object.activo = False
        self.object.save()
        messages.success(request, f'Rol "{self.object.nombre}" eliminado exitosamente')
        return redirect(self.success_url)