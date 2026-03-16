"""
URLs de la aplicación de usuarios
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # API Views
    RecuperarPasswordView,
    UsuarioViewSet,
    LoginView as LoginAPIView,
    LogoutView as LogoutAPIView,
    PerfilView as PerfilAPIView,
    ChangePasswordView,
    MeView,
    # Template Views
    LoginTemplateView,
    RegistroTemplateView,
    LogoutTemplateView,
    DashboardView,
    PerfilTemplateView,
)

# Router para el ViewSet (API)
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')

# URLs de API
api_urls = [
    path('', include(router.urls)),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/me/', MeView.as_view(), name='api-me'),
    path('auth/perfil/', PerfilAPIView.as_view(), name='api-perfil'),
    path('auth/cambiar-password/', ChangePasswordView.as_view(), name='api-cambiar-password'),
]

# URLs de Templates (Web)
template_urls = [
    path('login/', LoginTemplateView.as_view(), name='login'),
    path('registro/', RegistroTemplateView.as_view(), name='registro'),
    path('logout/', LogoutTemplateView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('perfil/', PerfilTemplateView.as_view(), name='perfil'),
    path('recuperar-password/', RecuperarPasswordView.as_view(), name='recuperar_password'),
]

urlpatterns = [
    # API endpoints (para la app móvil)
    path('api/', include(api_urls)),
    
    # Template URLs (para la web)
    path('', include(template_urls)),
]