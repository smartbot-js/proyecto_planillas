from apps.usuarios.models import Usuario

def admin_panel_context(request):
    """Context processor para contador de cuentas pendientes"""
    context = {}
    
    if request.user.is_authenticated:
        if request.user.is_superuser or (request.user.rol and request.user.rol.permisos.get('admin_panel', {}).get('acceso', False)):
            context['pendientes_aprobacion'] = Usuario.objects.filter(
                cuenta_aprobada=False, 
                is_active=True
            ).count()
    
    return context