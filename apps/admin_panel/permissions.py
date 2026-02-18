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
        messages.error(self.request, 'No tienes permisos para acceder a esta sección')
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

class PermissionRequiredMixin(UserPassesTestMixin):
    permission_modulo = None
    permission_accion = None

    def test_func(self):
        # SUPERUSER siempre puede todo
        if self.request.user.is_superuser:
            return True
        if not self.permission_modulo or not self.permission_accion:
            return False
        return self.request.user.tiene_permiso(self.permission_modulo, self.permission_accion)

    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permiso para realizar esta acción')
        return redirect('dashboard')