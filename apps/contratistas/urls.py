"""
URLs del módulo de Contratistas
apps/contratistas/urls.py
"""
from django.urls import path
from .views import (
    ContratistaDetalleView,
    ContratistaEstadoCuentaView,
    ContratistaListView,
    ContratistaCreateView,
    ContratistaUpdateView,
    ContratistaDetalleAPIView, 
    ContratistaEstadoCuentaAPIView,
    ContratoCreateView,
    ContratoDeleteView,
    ContratoUpdateView,
    ObtenerContratistasProyectoView,
    PagoAprobarContadorView,
    PagoAprobarGerenteView,
    PagoContratistaCreateView,
    PagoContratistaDeleteView,
    PagoContratistaDetalleView,
    PagoContratistaUpdateView,
    PagoRechazarView,
    PagosPendientesListView,
    PlanillaAprobarContadorView,
    PlanillaAprobarGerenteView,
    PlanillaCreateView,
    PlanillaDetalleView,
    PlanillaExportarExcelView,
    PlanillaListView,
    PlanillaMarcarPagadaView,
    PlanillaRechazarView,  
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

    path('contratistas/<int:pk>/',
         ContratistaDetalleView.as_view(),
         name='contratista_detalle'),
         
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

    # Gestión de pagos
    path('contratos/<int:contrato_id>/pagos/crear/',
         PagoContratistaCreateView.as_view(),
         name='pago_crear'),

    path('pagos/<int:pk>/editar/',
         PagoContratistaUpdateView.as_view(),
         name='pago_editar'),
    
    path('pagos/<int:pk>/eliminar/',
         PagoContratistaDeleteView.as_view(),
         name='pago_eliminar'),

    # Detalle del pago
    path('pagos/<int:pk>/',
         PagoContratistaDetalleView.as_view(),
         name='pago_detalle'),
    
    # Aprobaciones
    path('pagos/<int:pk>/aprobar-gerente/',
         PagoAprobarGerenteView.as_view(),
         name='pago_aprobar_gerente'),
    
    path('pagos/<int:pk>/aprobar-contador/',
         PagoAprobarContadorView.as_view(),
         name='pago_aprobar_contador'),
    
    path('pagos/<int:pk>/rechazar/',
         PagoRechazarView.as_view(),
         name='pago_rechazar'),
    
    # Lista de pagos pendientes
    path('pagos/pendientes/',
         PagosPendientesListView.as_view(),
         name='pagos_pendientes'),

     # ===========================================
     # PLANILLAS DE CONTRATISTAS
     # ===========================================
     path('planillas-contratistas/',
          PlanillaListView.as_view(),
          name='planillas_contratistas_lista'),

     path('planillas-contratistas/crear/',
          PlanillaCreateView.as_view(),
          name='planillas_contratistas_crear'),

     path('planillas-contratistas/<int:pk>/',
          PlanillaDetalleView.as_view(),
          name='planillas_contratistas_detalle'),

     path('planillas-contratistas/<int:pk>/aprobar-gerente/',
          PlanillaAprobarGerenteView.as_view(),
          name='planillas_contratistas_aprobar_gerente'),

     path('planillas-contratistas/<int:pk>/aprobar-contador/',
          PlanillaAprobarContadorView.as_view(),
          name='planillas_contratistas_aprobar_contador'),

     path('planillas-contratistas/<int:pk>/marcar-pagada/',
          PlanillaMarcarPagadaView.as_view(),
          name='planillas_contratistas_marcar_pagada'),

     path('planillas-contratistas/<int:pk>/rechazar/',
          PlanillaRechazarView.as_view(),
          name='planilla_contratista_rechazar'),
     # AJAX para obtener contratistas por proyecto
    path('api/contratistas-proyecto/', 
         ObtenerContratistasProyectoView.as_view(), 
         name='api_contratistas_proyecto'),
     
     path('planillas-contratistas/<int:pk>/exportar-excel/', 
         PlanillaExportarExcelView.as_view(), 
         name='planillas_contratistas_exportar_excel'),
     
         # Estado de cuenta (página completa)
    path('contratistas/<int:pk>/estado-cuenta-completo/', 
         ContratistaEstadoCuentaView.as_view(), 
         name='contratista_estado_cuenta'),
]
