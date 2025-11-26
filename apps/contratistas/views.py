"""
Vistas del módulo de Contratistas
apps/contratistas/views.py
"""
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from decimal import Decimal
from .models import Contratista, ContratoProyecto, PagoContratista
from apps.proyectos.models import Proyecto
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Contratista
from .forms import ContratistaForm
from apps.core.utils import get_tipo_cambio_actual

class ContratistaListView(LoginRequiredMixin, ListView):
    """Vista de lista de contratistas con filtros avanzados"""
    model = Contratista
    template_name = 'contratistas/lista.html'
    context_object_name = 'contratistas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contratista.objects.filter(eliminado=False).select_related('creado_por')
        
        # Filtro por búsqueda (cédula o nombre)
        buscar = self.request.GET.get('buscar', '').strip()
        if buscar:
            queryset = queryset.filter(
                Q(numero_cedula__icontains=buscar) |
                Q(nombre__icontains=buscar) |
                Q(apellido__icontains=buscar)
            )
        
        # Filtro por proyecto
        proyecto_id = self.request.GET.get('proyecto', '').strip()
        if proyecto_id:
            # Filtrar contratistas que tengan contratos en ese proyecto
            queryset = queryset.filter(
                contratos__proyecto_id=proyecto_id,
                contratos__eliminado=False
            ).distinct()
        
        # Filtro por forma de pago (de sus pagos)
        forma_pago = self.request.GET.get('forma_pago', '').strip()
        if forma_pago:
            queryset = queryset.filter(
                contratos__pagos__forma_pago=forma_pago,
                contratos__pagos__eliminado=False
            ).distinct()
        
        # Filtro por estado de contrato
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(
                contratos__estado=estado,
                contratos__eliminado=False
            ).distinct()
        
        return queryset.order_by('apellido', 'nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Tipo de cambio desde configuración global
        from apps.core.utils import get_tipo_cambio_actual
        tipo_cambio_global = get_tipo_cambio_actual()
        
        # Permitir override manual si el usuario lo cambia
        tipo_cambio = Decimal(self.request.GET.get('tipo_cambio', str(tipo_cambio_global)))
        moneda = self.request.GET.get('moneda', 'cordobas')  # cordobas o dolares
        
        context['tipo_cambio'] = tipo_cambio
        context['tipo_cambio_global'] = tipo_cambio_global
        context['moneda'] = moneda
        
        # Obtener listas para filtros
        context['proyectos'] = Proyecto.objects.filter(eliminado=False).order_by('nombre')
        context['formas_pago'] = PagoContratista.FORMA_PAGO_CHOICES
        context['estados_contrato'] = ContratoProyecto.ESTADO_CHOICES
        
        # Parámetros de búsqueda actuales
        context['buscar'] = self.request.GET.get('buscar', '')
        context['proyecto_seleccionado'] = self.request.GET.get('proyecto', '')
        context['forma_pago_seleccionada'] = self.request.GET.get('forma_pago', '')
        context['estado_seleccionado'] = self.request.GET.get('estado', '')
        
        # Calcular estadísticas generales
        contratistas_activos = Contratista.objects.filter(eliminado=False, activo=True)
        
        # Total de contratos
        total_contratos = ContratoProyecto.objects.filter(eliminado=False).count()
        
        # Total de pagos aprobados
        pagos_stats = PagoContratista.objects.filter(
            eliminado=False,
            estado='aprobado'
        ).aggregate(
            total_cordobas=Sum('monto_cordobas'),
            total_pagos=Count('id')
        )
        
        total_pagado_cordobas = pagos_stats['total_cordobas'] or Decimal('0.00')
        total_pagado_dolares = total_pagado_cordobas / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
        
        # Total valor de contratos
        valor_contratos = ContratoProyecto.objects.filter(
            eliminado=False
        ).aggregate(
            total=Sum('valor_contrato')
        )['total'] or Decimal('0.00')
        
        pendiente_cordobas = valor_contratos - total_pagado_cordobas
        pendiente_dolares = pendiente_cordobas / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
        
        # Porcentaje de avance general
        porcentaje_avance = (total_pagado_cordobas / valor_contratos * 100) if valor_contratos > 0 else 0
        
        context['stats'] = {
            'total_contratistas': contratistas_activos.count(),
            'total_contratos': total_contratos,
            'total_pagos': pagos_stats['total_pagos'] or 0,
            'total_pagado_cordobas': total_pagado_cordobas,
            'total_pagado_dolares': total_pagado_dolares,
            'valor_total_contratos': valor_contratos,
            'pendiente_cordobas': pendiente_cordobas,
            'pendiente_dolares': pendiente_dolares,
            'porcentaje_avance': porcentaje_avance,
        }
        
        # Agregar información de contratos y pagos a cada contratista
        for contratista in context['contratistas']:
            # Contratos del contratista
            contratos = ContratoProyecto.objects.filter(
                contratista=contratista,
                eliminado=False
            )
            
            # Total pagado al contratista
            total_pagado = PagoContratista.objects.filter(
                contrato__contratista=contratista,
                contrato__eliminado=False,
                eliminado=False,
                estado='aprobado'
            ).aggregate(total=Sum('monto_cordobas'))['total'] or Decimal('0.00')
            
            # Total valor de contratos del contratista
            valor_contratos_contratista = contratos.aggregate(
                total=Sum('valor_contrato')
            )['total'] or Decimal('0.00')
            
            # Pendiente
            pendiente = valor_contratos_contratista - total_pagado
            
            # Avance
            avance = (total_pagado / valor_contratos_contratista * 100) if valor_contratos_contratista > 0 else 0
            
            # Agregar al objeto
            contratista.total_contratos_count = contratos.count()
            contratista.valor_contratos = valor_contratos_contratista
            contratista.total_pagado_valor = total_pagado
            contratista.pendiente = pendiente
            contratista.avance = avance
            
            # Convertir a dólares si es necesario
            if moneda == 'dolares':
                contratista.valor_contratos_display = total_pagado / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
                contratista.total_pagado_display = total_pagado / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
                contratista.pendiente_display = pendiente / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
            else:
                contratista.valor_contratos_display = valor_contratos_contratista
                contratista.total_pagado_display = total_pagado
                contratista.pendiente_display = pendiente
        
        return context

class ContratistaCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo contratista"""
    model = Contratista
    form_class = ContratistaForm
    template_name = 'contratistas/crear.html'
    success_url = reverse_lazy('contratistas_lista')
    
    def form_valid(self, form):
        # Asignar el usuario que crea el contratista
        form.instance.creado_por = self.request.user
        
        messages.success(
            self.request,
            f'✅ Contratista {form.instance.nombre_completo} creado exitosamente.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            '❌ Error al crear el contratista. Por favor revisa los campos.'
        )
        return super().form_invalid(form)


class ContratistaUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para editar un contratista existente"""
    model = Contratista
    form_class = ContratistaForm
    template_name = 'contratistas/editar.html'
    success_url = reverse_lazy('contratistas_lista')
    
    def get_queryset(self):
        # Solo contratistas no eliminados
        return Contratista.objects.filter(eliminado=False)
    
    def form_valid(self, form):
        messages.success(
            self.request,
            f'✅ Contratista {form.instance.nombre_completo} actualizado exitosamente.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            '❌ Error al actualizar el contratista. Por favor revisa los campos.'
        )
        return super().form_invalid(form)

