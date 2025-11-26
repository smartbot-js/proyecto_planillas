"""
URLs principales del proyecto
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Redirigir raíz al login
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),
    
    # Usuarios (incluye API y Templates)
    path('', include('apps.usuarios.urls')),

    # Proyectos (incluye API y Templates)
    path('', include('apps.proyectos.urls')),
    path('', include('apps.trabajadores.urls')),
    path('', include('apps.asistencias.urls')),
    path('', include('apps.planillas.urls')),
    path('', include('apps.contratistas.urls')),

]

# API REST
from rest_framework.routers import DefaultRouter
from apps.trabajadores.views import TrabajadorViewSet
from apps.asistencias.views import AsistenciaViewSet  # ← AGREGAR

router = DefaultRouter()
router.register(r'trabajadores', TrabajadorViewSet, basename='trabajador')
router.register(r'asistencias', AsistenciaViewSet, basename='asistencia')  # ← AGREGAR

urlpatterns += [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]

# Servir archivos media y static en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    