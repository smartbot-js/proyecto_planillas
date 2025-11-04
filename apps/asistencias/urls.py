"""
URLs para el módulo de asistencias
"""

from django.urls import path
from .views import (
    AsistenciaAgregarNotaView,
    AsistenciaHistorialView,
    AsistenciaListView,
    AsistenciaDetalleView,
    AsistenciaMarcarEntradaView,
    AsistenciaCerrarTurnoView,
    AsistenciaEditarView,
    AsistenciaReportesView,
    asistencias_exportar_csv,
)

urlpatterns = [
    # Vistas principales
    path('asistencias/', AsistenciaListView.as_view(), name='asistencias_lista'),
    path('asistencias/<int:pk>/', AsistenciaDetalleView.as_view(), name='asistencia_detalle'),
    
    # Acciones
    path('asistencias/marcar-entrada/', AsistenciaMarcarEntradaView.as_view(), name='asistencia_marcar_entrada'),
    path('asistencias/<int:pk>/cerrar-turno/', AsistenciaCerrarTurnoView.as_view(), name='asistencia_cerrar_turno'),
    path('asistencias/<int:pk>/editar/', AsistenciaEditarView.as_view(), name='asistencia_editar'),
    
    # Reportes
    path('asistencias/reportes/', AsistenciaReportesView.as_view(), name='asistencias_reportes'),
    path('asistencias/exportar/', asistencias_exportar_csv, name='asistencias_exportar'),
    path('<int:pk>/agregar-nota/', AsistenciaAgregarNotaView.as_view(), name='asistencia_agregar_nota'),
    path('trabajador/<int:trabajador_id>/historial/', AsistenciaHistorialView.as_view(), name='asistencia_historial')
]
