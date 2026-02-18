from django.urls import path
from .views import (
    AsignarProyectosUsuarioView,
    UsuariosListView,
    AprobarCuentaView,
    CambiarEstadoUsuarioView,
    AsignarRolView,
    RolesListView,
    RolCreateView,
    RolUpdateView,
    RolDeleteView,
)

app_name = 'admin_panel'

urlpatterns = [
    # Usuarios
    path('usuarios/', UsuariosListView.as_view(), name='usuarios_lista'),
    path('usuarios/<int:pk>/aprobar/', AprobarCuentaView.as_view(), name='aprobar_cuenta'),
    path('usuarios/<int:pk>/cambiar-estado/', CambiarEstadoUsuarioView.as_view(), name='cambiar_estado_usuario'),
    path('usuarios/<int:pk>/asignar-rol/', AsignarRolView.as_view(), name='asignar_rol'),
    path('usuarios/<int:pk>/proyectos/', AsignarProyectosUsuarioView.as_view(), name='asignar_proyectos'),

    # Roles
    path('roles/', RolesListView.as_view(), name='roles_lista'),
    path('roles/crear/', RolCreateView.as_view(), name='rol_crear'),
    path('roles/<int:pk>/editar/', RolUpdateView.as_view(), name='rol_editar'),
    path('roles/<int:pk>/eliminar/', RolDeleteView.as_view(), name='rol_eliminar'),
]