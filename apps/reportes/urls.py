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
]