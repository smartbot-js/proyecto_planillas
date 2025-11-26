"""
URLs del módulo de Contratistas
apps/contratistas/urls.py
"""
from django.urls import path
from .views import (
    ContratistaListView,
    ContratistaCreateView,
    ContratistaUpdateView,
    )

urlpatterns = [
    # Lista de contratistas
    path('contratistas/', ContratistaListView.as_view(), name='contratistas_lista'),
    
    # Crear contratista
    path('contratistas/crear/', ContratistaCreateView.as_view(), name='contratistas_crear'),
    
    # Editar contratista
    path('contratistas/<int:pk>/editar/', ContratistaUpdateView.as_view(), name='contratistas_editar'),

]
