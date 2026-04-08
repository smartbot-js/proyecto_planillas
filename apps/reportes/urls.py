"""
URLs del módulo de Reportes
apps/reportes/urls.py
"""
from django.urls import path
from .views import (
    ReportesIndexView,
    ReportePorProyectoView,
    ReportePlanillaAdministrativaView,
    ReporteGastosVariosView,
    ReporteConsolidadoProyectosView,
    ReportePlanillaTotalView,
    ExportarReporteProyectoExcelView,
    ExportarConsolidadoExcelView,
    ExportarAdministrativaExcelView,
    ExportarGastosVariosExcelView,
    ExportarPlanillaTotalExcelView,
)
from .views_gastos import (
    ReporteGastosExportarExcelView,
    ReporteGastosExportarPDFView,
    ReporteGastosListView,
    ReporteGastosCreateView,
    ReporteGastosDetalleView,
    ReporteGastosAgregarLineaView,
    ReporteGastosEditarLineaView,
    ReporteGastosEliminarLineaView,
    ReporteGastosAprobarGerenteView,
    ReporteGastosAprobarContadorView,
    ReporteGastosMarcarPagadaView,
    ReporteGastosAnularView,
)

urlpatterns = [
    # Índice principal de reportes
    path('reportes/', ReportesIndexView.as_view(), name='reportes_index'),
    
    # Reporte por proyecto individual
    path('reportes/proyecto/', ReportePorProyectoView.as_view(), name='reporte_proyecto'),
    
    # Planilla administrativa
    path('reportes/administrativa/', ReportePlanillaAdministrativaView.as_view(), name='reporte_administrativa'),
    
    # Reembolsos y gastos varios
    path('reportes/gastos-varios/', ReporteGastosVariosView.as_view(), name='reporte_gastos_varios'),
    
    # Consolidado de todos los proyectos
    #path('reportes/consolidado-proyectos/', ReporteConsolidadoProyectosView.as_view(), name='reporte_consolidado_proyectos'),
    path('reportes/consolidado/', ReporteConsolidadoProyectosView.as_view(), name='reporte_consolidado'),

    
    # Planilla total (consolidado general)
    path('reportes/planilla-total/', ReportePlanillaTotalView.as_view(), name='reporte_planilla_total'),

    # Exportaciones Excel
    path('reportes/proyecto/exportar-excel/', ExportarReporteProyectoExcelView.as_view(), name='reporte_proyecto_excel'),
    path('reportes/consolidado/exportar-excel/', ExportarConsolidadoExcelView.as_view(), name='exportar_consolidado_excel'),
    path('reportes/administrativa/exportar-excel/', ExportarAdministrativaExcelView.as_view(), name='exportar_administrativa_excel'),
    path('reportes/gastos-varios/exportar-excel/', ExportarGastosVariosExcelView.as_view(), name='exportar_gastos_excel'),
    path('reportes/planilla-total/exportar-excel/', ExportarPlanillaTotalExcelView.as_view(), name='exportar_planilla_total_excel'),

    # ============================================================
    # GASTOS Y REEMBOLSOS (CRUD)
    # ============================================================
    path('reportes/gastos-reembolsos/', ReporteGastosListView.as_view(), name='gastos_reembolsos_lista'),
    path('reportes/gastos-reembolsos/crear/', ReporteGastosCreateView.as_view(), name='gastos_reembolsos_crear'),
    path('reportes/gastos-reembolsos/<int:pk>/', ReporteGastosDetalleView.as_view(), name='gastos_reembolsos_detalle'),
    path('reportes/gastos-reembolsos/<int:pk>/agregar-linea/', ReporteGastosAgregarLineaView.as_view(), name='gastos_reembolsos_agregar_linea'),
    path('reportes/gastos-reembolsos/<int:pk>/editar-linea/<int:linea_pk>/', ReporteGastosEditarLineaView.as_view(), name='gastos_reembolsos_editar_linea'),
    path('reportes/gastos-reembolsos/<int:pk>/eliminar-linea/<int:linea_pk>/', ReporteGastosEliminarLineaView.as_view(), name='gastos_reembolsos_eliminar_linea'),
    path('reportes/gastos-reembolsos/<int:pk>/aprobar-gerente/', ReporteGastosAprobarGerenteView.as_view(), name='gastos_reembolsos_aprobar_gerente'),
    path('reportes/gastos-reembolsos/<int:pk>/aprobar-contador/', ReporteGastosAprobarContadorView.as_view(), name='gastos_reembolsos_aprobar_contador'),
    path('reportes/gastos-reembolsos/<int:pk>/marcar-pagada/', ReporteGastosMarcarPagadaView.as_view(), name='gastos_reembolsos_marcar_pagada'),
    path('reportes/gastos-reembolsos/<int:pk>/anular/', ReporteGastosAnularView.as_view(), name='gastos_reembolsos_anular'),
    path('reportes/gastos-reembolsos/<int:pk>/exportar-excel/', ReporteGastosExportarExcelView.as_view(), name='gastos_reembolsos_exportar_excel'),
    path('reportes/gastos-reembolsos/<int:pk>/exportar-pdf/', ReporteGastosExportarPDFView.as_view(), name='gastos_reembolsos_exportar_pdf'),

]