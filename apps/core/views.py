"""
Vistas adicionales para apps/core
"""

from django.http import JsonResponse
from django.views import View
from .nicaragua_data import get_municipios, DEPARTAMENTOS, NICARAGUA_DATA
from .puestos_data import get_puestos, AREAS_TRABAJO, PUESTOS_DATA


class MunicipiosAPIView(View):
    """
    API para obtener municipios de un departamento
    
    GET /api/core/municipios/?departamento=Managua
    
    Returns:
        JSON: {"municipios": ["Ciudad Sandino", "El Crucero", ...]}
    """
    
    def get(self, request):
        departamento = request.GET.get('departamento', '')
        
        if not departamento:
            return JsonResponse({
                'error': 'Debe especificar un departamento',
                'municipios': []
            }, status=400)
        
        municipios = get_municipios(departamento)
        
        if not municipios:
            return JsonResponse({
                'error': f'Departamento "{departamento}" no encontrado',
                'municipios': []
            }, status=404)
        
        return JsonResponse({
            'departamento': departamento,
            'municipios': municipios
        })


class DepartamentosAPIView(View):
    """
    API para obtener todos los departamentos
    
    GET /api/core/departamentos/
    
    Returns:
        JSON: {"departamentos": ["Boaco", "Carazo", ...]}
    """
    
    def get(self, request):
        return JsonResponse({
            'departamentos': DEPARTAMENTOS
        })


class UbicacionesAPIView(View):
    """
    API para obtener todos los departamentos con sus municipios
    
    GET /api/core/ubicaciones/
    
    Returns:
        JSON: {"data": {"Managua": ["Ciudad Sandino", ...], ...}}
    """
    
    def get(self, request):
        return JsonResponse({
            'data': NICARAGUA_DATA
        })

class PuestosAPIView(View):
    """
    API para obtener puestos de un área de trabajo
    
    GET /api/core/puestos-por-area/?area=Oficiales
    
    Returns:
        JSON: {"puestos": ["Albañil", "Fontanero"]}
    """
    
    def get(self, request):
        area = request.GET.get('area', '')
        
        if not area:
            # Si no se especifica área, devolver todos los datos
            return JsonResponse({
                'data': PUESTOS_DATA
            })
        
        puestos = get_puestos(area)
        
        if not puestos:
            return JsonResponse({
                'error': f'Área "{area}" no encontrada',
                'puestos': []
            }, status=404)
        
        return JsonResponse({
            'area': area,
            'puestos': puestos
        })


class AreasTrabajoAPIView(View):
    """
    API para obtener todas las áreas de trabajo
    
    GET /api/core/areas-trabajo/
    
    Returns:
        JSON: {"areas": ["Administración", "Oficiales", ...]}
    """
    
    def get(self, request):
        return JsonResponse({
            'areas': AREAS_TRABAJO
        })


class PuestosCompletosAPIView(View):
    """
    API para obtener todas las áreas con sus puestos
    
    GET /api/core/puestos/
    
    Returns:
        JSON: {"data": {"Administración": ["Seguridad", ...], ...}}
    """
    
    def get(self, request):
        return JsonResponse({
            'data': PUESTOS_DATA
        })
        