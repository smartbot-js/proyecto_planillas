"""
URLs para el módulo de asistencias
"""

from django.urls import path
from .views import (
    AsistenciaAgregarNotaView,
    AsistenciaHistorialView,
    AsistenciaJustificadaView,
    AsistenciaListView,
    AsistenciaDetalleView,
    AsistenciaMarcarEntradaView,
    AsistenciaCerrarTurnoView,
    AsistenciaEditarView,
    AsistenciaReportesView,
    AsistenciaValidarTodasView,
    asistencias_exportar_csv,
    AsistenciaValidarListView,
    AsistenciaValidarView,
    AsistenciaCorregirView,
)

urlpatterns = [
    # Vistas principales
    path('asistencias/', AsistenciaListView.as_view(), name='asistencias_lista'),
    path('asistencias/<int:pk>/', AsistenciaDetalleView.as_view(), name='asistencia_detalle'),
    
    # Acciones
    path('asistencias/marcar-entrada/', AsistenciaMarcarEntradaView.as_view(), name='asistencia_marcar_entrada'),
    path('asistencias/justificada/', AsistenciaJustificadaView.as_view(), name='asistencia_justificada'),
    path('asistencias/<int:pk>/cerrar-turno/', AsistenciaCerrarTurnoView.as_view(), name='asistencia_cerrar_turno'),
    path('asistencias/<int:pk>/editar/', AsistenciaEditarView.as_view(), name='asistencia_editar'),
    
    # Reportes
    path('asistencias/reportes/', AsistenciaReportesView.as_view(), name='asistencias_reportes'),
    path('asistencias/exportar/', asistencias_exportar_csv, name='asistencias_exportar'),
    path('<int:pk>/agregar-nota/', AsistenciaAgregarNotaView.as_view(), name='asistencia_agregar_nota'),
    path('trabajador/<int:trabajador_id>/historial/', AsistenciaHistorialView.as_view(), name='asistencia_historial'),

    # Validación de asistencias
    path('validar/', AsistenciaValidarListView.as_view(), name='asistencias_validar_lista'),
    path('validar-todas/', AsistenciaValidarTodasView.as_view(), name='asistencias_validar_todas'),
    path('<int:pk>/validar/', AsistenciaValidarView.as_view(), name='asistencia_validar'),
    path('<int:pk>/corregir/', AsistenciaCorregirView.as_view(), name='asistencia_corregir'),


]
