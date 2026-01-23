"""
URLs de la aplicación core
apps/core/urls.py
"""

from django.urls import path
from .views import (MunicipiosAPIView, DepartamentosAPIView, UbicacionesAPIView,
                    PuestosAPIView, AreasTrabajoAPIView, PuestosCompletosAPIView)

urlpatterns = [
    # API de ubicaciones de Nicaragua
    path('api/core/municipios/', MunicipiosAPIView.as_view(), name='api_municipios'),
    path('api/core/departamentos/', DepartamentosAPIView.as_view(), name='api_departamentos'),
    path('api/core/ubicaciones/', UbicacionesAPIView.as_view(), name='api_ubicaciones'),

    # Puestos laborales (AGREGAR)
    path('api/core/puestos/', PuestosCompletosAPIView.as_view(), name='api_puestos'),
    path('api/core/puestos-por-area/', PuestosAPIView.as_view(), name='api_puestos_por_area'),
    path('api/core/areas-trabajo/', AreasTrabajoAPIView.as_view(), name='api_areas_trabajo'),

]