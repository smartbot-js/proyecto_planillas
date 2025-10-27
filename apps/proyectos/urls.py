"""
URLs de la aplicación de proyectos
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # API Views
    ProyectoViewSet,
    # Template Views
    ProyectoListView,
    ProyectoCreateView,
    ProyectoDetalleView,
    ProyectoEditarView,
    ProyectoEliminarView,
    ProyectoRestaurarView,
    ProyectosEliminadosView,
    ProyectoToggleActivoView,
)

# Router para el ViewSet (API)
router = DefaultRouter()
router.register(r'proyectos', ProyectoViewSet, basename='proyecto')

# URLs de API
api_urls = [
    path('', include(router.urls)),
]

# URLs de Templates (Web)
template_urls = [
    path('proyectos/', ProyectoListView.as_view(), name='proyectos_lista'),
    path('proyectos/crear/', ProyectoCreateView.as_view(), name='proyecto_crear'),
    path('proyectos/<int:pk>/', ProyectoDetalleView.as_view(), name='proyecto_detalle'),
    path('proyectos/<int:pk>/editar/', ProyectoEditarView.as_view(), name='proyecto_editar'),
    path('proyectos/<int:pk>/eliminar/', ProyectoEliminarView.as_view(), name='proyecto_eliminar'),
    path('proyectos/<int:pk>/restaurar/', ProyectoRestaurarView.as_view(), name='proyecto_restaurar'),
    path('proyectos/<int:pk>/toggle-activo/', ProyectoToggleActivoView.as_view(), name='proyecto_toggle_activo'),
    path('proyectos/eliminados/', ProyectosEliminadosView.as_view(), name='proyectos_eliminados'),
]

urlpatterns = [
    # API endpoints (para la app móvil)
    path('api/', include(api_urls)),
    
    # Template URLs (para la web)
    path('', include(template_urls)),
]