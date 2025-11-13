"""
URLs de la aplicación de planillas - CORREGIDO
apps/planillas/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Template Views
    PlanillaListView,
    PlanillaCreateView,
    PlanillaListView,
    PlanillaCreateView,
    PlanillaDetalleView,
    PlanillaEditarDetalleView,
    PlanillaAprobarGerenteView,
    PlanillaAprobarContadorView,
    PlanillaMarcarPagadaView,
    PlanillaEliminarView,
    PlanillaExportarExcelView,
    PlanillaExportarPDFView,
)

# Router para el ViewSet (API) - para futuro
router = DefaultRouter()
# router.register(r'planillas', PlanillaViewSet, basename='planilla')

# URLs de API (para app móvil - futuro)
api_urls = [
    path('', include(router.urls)),
]

# URLs de Templates (Web)
urlpatterns = [
    # API endpoints (para la app móvil)
    path('api/', include(api_urls)),
    
    # Lista de planillas
    path('planillas/', PlanillaListView.as_view(), name='planillas_lista'),
    
    # Crear planilla
    path('planillas/crear/', PlanillaCreateView.as_view(), name='planilla_crear'),
    
    # Detalle de planilla
    path('planillas/<int:pk>/', PlanillaDetalleView.as_view(), name='planilla_detalle'),
    
    # Editar detalle (bonos/deducciones)
    path('planillas/detalle/<int:pk>/editar/', PlanillaEditarDetalleView.as_view(), name='planilla_editar_detalle'),
    
    # Acciones de aprobación
    path('planillas/<int:pk>/aprobar-gerente/', PlanillaAprobarGerenteView.as_view(), name='planilla_aprobar_gerente'),
    path('planillas/<int:pk>/aprobar-contador/', PlanillaAprobarContadorView.as_view(), name='planilla_aprobar_contador'),
    path('planillas/<int:pk>/marcar-pagada/', PlanillaMarcarPagadaView.as_view(), name='planilla_marcar_pagada'),
    
    # Eliminar planilla
    path('planillas/<int:pk>/eliminar/', PlanillaEliminarView.as_view(), name='planilla_eliminar'),

    # Exportar Planillas    
    path('planillas/<int:pk>/exportar-excel/', PlanillaExportarExcelView.as_view(), name='planilla_exportar_excel'),
    path('planillas/<int:pk>/exportar-pdf/', PlanillaExportarPDFView.as_view(), name='planilla_exportar_pdf'),

    # Acciones (próximamente)
    # path('planillas/<int:pk>/aprobar-gerente/', ..., name='planilla_aprobar_gerente'),
    # path('planillas/<int:pk>/aprobar-contador/', ..., name='planilla_aprobar_contador'),
    # path('planillas/<int:pk>/pagar/', ..., name='planilla_pagar'),
    
    # Exportación (próximamente)
    # path('planillas/<int:pk>/exportar-excel/', ..., name='planilla_exportar_excel'),
    # path('planillas/<int:pk>/exportar-pdf/', ..., name='planilla_exportar_pdf'),
]