"""
URLs del módulo de Contratistas
apps/contratistas/urls.py
"""
from django.urls import path
from .views import (
    ContratistaListView,
    ContratistaCreateView,
    ContratistaUpdateView,
    ContratistaDetalleAPIView, 
    ContratistaEstadoCuentaAPIView,
    ContratoCreateView,
    ContratoDeleteView,
    ContratoUpdateView,  
    )

urlpatterns = [
    # Lista de contratistas
    path('contratistas/', ContratistaListView.as_view(), name='contratistas_lista'),
    
    # Crear contratista
    path('contratistas/crear/', ContratistaCreateView.as_view(), name='contratistas_crear'),
    
    # Editar contratista
    path('contratistas/<int:pk>/editar/', ContratistaUpdateView.as_view(), name='contratistas_editar'),

    # ✅ NUEVO: Detalle del contratista (API JSON)
    path('contratistas/<int:pk>/detalle/', 
         ContratistaDetalleAPIView.as_view(), 
         name='contratista_detalle_api'),
    
    # ✅ NUEVO: Estado de cuenta (API JSON)
    path('contratistas/<int:pk>/estado-cuenta/', 
         ContratistaEstadoCuentaAPIView.as_view(), 
         name='contratista_estado_cuenta_api'),

# Gestión de contratos
    path('proyectos/<int:proyecto_id>/contratos/crear/', 
         ContratoCreateView.as_view(), 
         name='contrato_crear'),
    
    path('contratos/<int:pk>/editar/', 
         ContratoUpdateView.as_view(), 
         name='contrato_editar'),
    
    path('contratos/<int:pk>/eliminar/', 
         ContratoDeleteView.as_view(), 
         name='contrato_eliminar'),
]
