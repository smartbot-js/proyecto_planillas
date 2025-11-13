"""
Permisos personalizados para el módulo de asistencias

"""

from rest_framework import permissions


class EsSupervisorDelProyecto(permissions.BasePermission):
    """
    Permiso que verifica si el usuario es supervisor del proyecto
    de la asistencia
    """
    
    message = 'Solo el supervisor del proyecto puede realizar esta acción.'
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto (Asistencia)
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
            obj: Objeto Asistencia
        
        Returns:
            bool: True si tiene permiso
        """
        # Administradores siempre pueden
        if request.user.es_administrador():
            return True
        
        # Supervisores solo si es su proyecto
        if request.user.es_supervisor():
            return obj.proyecto.supervisor == request.user
        
        return False


class PuedeValidarAsistencias(permissions.BasePermission):
    """
    Permiso que verifica si el usuario puede validar asistencias
    (Administrador o Supervisor)
    """
    
    message = 'Solo administradores y supervisores pueden validar asistencias.'
    
    def has_permission(self, request, view):
        """
        Verifica permisos a nivel de vista
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
        
        Returns:
            bool: True si tiene permiso
        """
        return (
            request.user.is_authenticated and
            (request.user.es_administrador() or request.user.es_supervisor())
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
            obj: Objeto Asistencia
        
        Returns:
            bool: True si tiene permiso
        """
        # Administradores siempre pueden
        if request.user.es_administrador():
            return True
        
        # Supervisores solo si es su proyecto
        if request.user.es_supervisor():
            return obj.proyecto.supervisor == request.user
        
        return False


class PuedeCorregirAsistencias(permissions.BasePermission):
    """
    Permiso que verifica si el usuario puede corregir marcaciones
    """
    
    message = 'Solo administradores y supervisores del proyecto pueden corregir marcaciones.'
    
    def has_permission(self, request, view):
        """
        Verifica permisos a nivel de vista
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
        
        Returns:
            bool: True si tiene permiso
        """
        return (
            request.user.is_authenticated and
            (request.user.es_administrador() or request.user.es_supervisor())
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto (Asistencia)
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
            obj: Objeto Asistencia
        
        Returns:
            bool: True si tiene permiso
        """
        # Administradores siempre pueden
        if request.user.es_administrador():
            return True
        
        # Supervisores solo si es su proyecto
        if request.user.es_supervisor():
            return obj.proyecto.supervisor == request.user
        
        return False


class PuedeVerAsistencias(permissions.BasePermission):
    """
    Permiso que verifica si el usuario puede ver asistencias
    """
    
    message = 'No tienes permiso para ver estas asistencias.'
    
    def has_permission(self, request, view):
        """
        Todos los usuarios autenticados pueden ver asistencias
        (pero filtradas por proyecto)
        """
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto
        
        Args:
            request: Request HTTP
            view: Vista que se está ejecutando
            obj: Objeto Asistencia
        
        Returns:
            bool: True si tiene permiso
        """
        # Administradores pueden ver todo
        if request.user.es_administrador():
            return True
        
        # Supervisores pueden ver asistencias de sus proyectos
        if request.user.es_supervisor():
            return obj.proyecto.supervisor == request.user
        
        # Trabajadores solo pueden ver sus propias asistencias
        if request.user.es_trabajador():
            # Buscar si hay un trabajador asociado a este usuario
            try:
                from apps.trabajadores.models import Trabajador
                trabajador = Trabajador.objects.get(email=request.user.email, eliminado=False)
                return obj.trabajador == trabajador
            except:
                return False
        
        return False