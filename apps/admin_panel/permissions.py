from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin

def superadmin_required(view_func):
    """Decorador para vistas función que requieren super admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superuser or (request.user.rol and request.user.rol.codigo == 'admin')):
            messages.error(request, 'No tienes permisos para acceder a esta sección')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin para vistas clase que requieren super admin"""
    def test_func(self):
        return self.request.user.is_superuser or \
               (self.request.user.rol and self.request.user.rol.codigo == 'admin')
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('login')
        modulo = getattr(self, 'permission_modulo', None) or 'sistema'
        accion = getattr(self, 'permission_accion', None) or 'acceder'
        rol_nombre = self.request.user.rol.nombre if self.request.user.rol else 'Sin rol'
        messages.error(
            self.request,
            f'⛔ Tu rol ({rol_nombre}) no tiene permiso para "{accion}" en "{modulo}". '
            f'Contacta al administrador si necesitas este acceso.'
        )
        # Volver a la página donde estaba, no al dashboard
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('dashboard')

def permission_required(modulo, accion):
    """Decorador genérico para permisos"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not request.user.tiene_permiso(modulo, accion):
                messages.error(request, f'No tienes permiso para realizar esta acción')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

class PermissionRequiredMixin:
    """Mixin de permisos basado en el JSON del rol"""
    permission_modulo = None
    permission_accion = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Superuser siempre puede
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar permiso
        if self.permission_modulo and self.permission_accion:
            if not request.user.tiene_permiso(self.permission_modulo, self.permission_accion):
                rol_nombre = request.user.rol.nombre if request.user.rol else 'Sin rol'
                messages.error(
                    request,
                    f'⛔ Tu rol ({rol_nombre}) no tiene permiso para "{self.permission_accion}" en "{self.permission_modulo}". '
                    f'Contacta al administrador si necesitas este acceso.'
                )
                referer = request.META.get('HTTP_REFERER')
                if referer:
                    return redirect(referer)
                return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)