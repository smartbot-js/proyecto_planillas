"""
URLs para el módulo de trabajadores
"""

from django.urls import path
from .views import (
    TrabajadorListView,
    TrabajadorCreateView,
    TrabajadorDetalleView,
    TrabajadorEditarView,
    TrabajadorEliminarView,
    TrabajadorRegenerarTodosQRView,
    TrabajadorTrasladarView,
    TrabajadorImportarCSVView,
    TrabajadorImportarConfirmarView,
    TrabajadorGenerarQRView,
    trabajadores_exportar,
    trabajadores_plantilla_csv,
)

urlpatterns = [
    # Vistas principales
    path('trabajadores/', TrabajadorListView.as_view(), name='trabajadores_lista'),
    path('trabajadores/crear/', TrabajadorCreateView.as_view(), name='trabajador_crear'),
    path('trabajadores/<int:pk>/', TrabajadorDetalleView.as_view(), name='trabajador_detalle'),
    path('trabajadores/<int:pk>/editar/', TrabajadorEditarView.as_view(), name='trabajador_editar'),
    path('trabajadores/<int:pk>/eliminar/', TrabajadorEliminarView.as_view(), name='trabajador_eliminar'),
    path('trabajadores/<int:pk>/trasladar/', TrabajadorTrasladarView.as_view(), name='trabajador_trasladar'),
    
    # Código QR
    path('trabajadores/<int:pk>/generar-qr/', TrabajadorGenerarQRView.as_view(), name='trabajador_generar_qr'),
    
    # Importación y exportación CSV
    path('trabajadores/importar-csv/', TrabajadorImportarCSVView.as_view(), name='trabajadores_importar_csv'),
    path('trabajadores/importar-csv/confirmar/', TrabajadorImportarConfirmarView.as_view(), name='trabajadores_importar_confirmar'),
    path('trabajadores/exportar/', trabajadores_exportar, name='trabajadores_exportar'),
    path('trabajadores/plantilla-csv/', trabajadores_plantilla_csv, name='trabajadores_plantilla_csv'),

    # Código QR
    path('trabajadores/<int:pk>/generar-qr/', TrabajadorGenerarQRView.as_view(), name='trabajador_generar_qr'),
    path('trabajadores/regenerar-todos-qr/', TrabajadorRegenerarTodosQRView.as_view(), name='trabajadores_regenerar_todos_qr'),

]