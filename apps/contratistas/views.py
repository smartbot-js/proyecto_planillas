"""
Vistas del módulo de Contratistas - MEJORADO FASE 1
apps/contratistas/views.py
"""
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from decimal import Decimal
from datetime import datetime
import decimal  # Para manejar excepciones de Decimal

from .models import Contratista, ContratoProyecto, AvaluoContratista, PlanillaContratista, DetallePlanillaContratista
from apps.proyectos.models import Proyecto
from .forms import ContratistaForm, ContratoProyectoForm, PagoContratistaForm
from apps.core.utils import get_tipo_cambio_actual

from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404,redirect


PagoContratista = AvaluoContratista

class ContratistaListView(LoginRequiredMixin, ListView):
    """Vista de lista de contratistas con filtros avanzados"""
    model = Contratista
    template_name = 'contratistas/lista.html'
    context_object_name = 'contratistas'
    paginate_by = 50  # ✅ CAMBIADO: De 20 a 50 items por página
    
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
        
        # ✅ NUEVO: Filtro por rango de fechas de contrato
        fecha_desde = self.request.GET.get('fecha_desde', '').strip()
        fecha_hasta = self.request.GET.get('fecha_hasta', '').strip()
        
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    contratos__fecha_inicio__gte=fecha_desde_obj,
                    contratos__eliminado=False
                ).distinct()
            except ValueError:
                pass  # Ignorar si la fecha no es válida
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    contratos__fecha_inicio__lte=fecha_hasta_obj,
                    contratos__eliminado=False
                ).distinct()
            except ValueError:
                pass  # Ignorar si la fecha no es válida
        
        return queryset.order_by('apellido', 'nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Tipo de cambio desde configuración global
        tipo_cambio_global = get_tipo_cambio_actual()
        
        # Permitir override manual si el usuario lo cambia
        # Manejar tipo_cambio vacío o inválido
        tipo_cambio_param = self.request.GET.get('tipo_cambio', '').strip()
        if tipo_cambio_param:
            try:
                tipo_cambio = Decimal(tipo_cambio_param)
                # Validar que sea mayor que 0
                if tipo_cambio <= 0:
                    tipo_cambio = tipo_cambio_global
            except (ValueError, decimal.InvalidOperation):
                tipo_cambio = tipo_cambio_global
        else:
            tipo_cambio = tipo_cambio_global
        
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
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')  # ✅ NUEVO
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')  # ✅ NUEVO
        
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
            
            # Cantidad de pagos realizados
            cantidad_pagos = PagoContratista.objects.filter(
                contrato__contratista=contratista,
                contrato__eliminado=False,
                eliminado=False,
                estado='aprobado'
            ).count()
            
            # Agregar al objeto
            contratista.total_contratos_count = contratos.count()
            contratista.valor_contratos = valor_contratos_contratista
            contratista.total_pagado_valor = total_pagado
            contratista.pendiente = pendiente
            contratista.avance = avance
            contratista.cantidad_pagos = cantidad_pagos  # ✅ NUEVO
            
            # Convertir a dólares si es necesario
            if moneda == 'dolares':
                contratista.valor_contratos_display = valor_contratos_contratista / tipo_cambio if tipo_cambio > 0 else Decimal('0.00')
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
    

class ContratistaDetalleAPIView(LoginRequiredMixin, View):
    """
    API para obtener el detalle completo de un contratista
    Retorna JSON con toda la información
    """
    
    def get(self, request, pk):
        try:
            # Obtener contratista
            contratista = get_object_or_404(Contratista, pk=pk, eliminado=False)
            
            # Obtener tipo de cambio
            tipo_cambio = get_tipo_cambio_actual()
            
            # Datos básicos del contratista
            data = {
                'id': contratista.id,
                'nombre_completo': contratista.nombre_completo,
                'nombre': contratista.nombre,
                'apellido': contratista.apellido,
                'numero_cedula': contratista.numero_cedula,
                'telefono': contratista.telefono or '-',
                'direccion': contratista.direccion or '-',
                'departamento': contratista.departamento or '-',
                'municipio': contratista.municipio or '-',
                'foto_cedula_url': contratista.foto_cedula.url if contratista.foto_cedula else None,
                
                # Datos bancarios
                'banco': contratista.banco or '-',
                'numero_cuenta': contratista.numero_cuenta or '-',
                'tipo_cuenta': contratista.get_tipo_cuenta_display() if contratista.tipo_cuenta else '-',
                'moneda_cuenta': contratista.get_moneda_cuenta_display() if contratista.moneda_cuenta else '-',
                
                # Metadata
                'activo': contratista.activo,
                'fecha_creacion': contratista.creado_en.strftime('%d/%m/%Y %H:%M'),
                
                # Contratos
                'contratos': [],
                
                # Resumen financiero
                'total_contratos': 0,
                'valor_total_contratos': Decimal('0.00'),
                'total_pagado': Decimal('0.00'),
                'total_pendiente': Decimal('0.00'),
                'porcentaje_avance': 0,
                'cantidad_pagos': 0,
            }
            
            # Obtener contratos del contratista
            contratos = ContratoProyecto.objects.filter(
                contratista=contratista,
                eliminado=False
            ).select_related('proyecto').order_by('-fecha_inicio')
            
            data['total_contratos'] = contratos.count()
            
            contratos_list = []
            total_valor = Decimal('0.00')
            total_pagado = Decimal('0.00')
            
            for contrato in contratos:
                # Pagos del contrato
                pagos = PagoContratista.objects.filter(
                    contrato=contrato,
                    eliminado=False,
                    estado='aprobado'
                ).order_by('-fecha_pago')
                
                pagado_contrato = pagos.aggregate(
                    total=Sum('monto_cordobas')
                )['total'] or Decimal('0.00')
                
                pendiente_contrato = contrato.valor_contrato - pagado_contrato
                avance_contrato = (pagado_contrato / contrato.valor_contrato * 100) if contrato.valor_contrato > 0 else 0
                
                # Lista de pagos del contrato
                pagos_list = []
                for pago in pagos:
                    pagos_list.append({
                        'id': pago.id,
                        'codigo': pago.codigo,
                        'fecha': pago.fecha_pago.strftime('%d/%m/%Y'),
                        'concepto': pago.concepto,
                        'monto_cordobas': float(pago.monto_cordobas),
                        'monto_dolares': float(pago.monto_dolares),
                        'forma_pago': pago.get_forma_pago_display(),
                        'estado': pago.get_estado_display(),
                        'archivo_soporte': pago.archivo_soporte.url if pago.archivo_soporte else None,
                    })
                
                contratos_list.append({
                    'id': contrato.id,
                    'codigo': contrato.codigo,
                    'proyecto': {
                        'id': contrato.proyecto.id,
                        'nombre': contrato.proyecto.nombre,
                        'descripcion': contrato.proyecto.descripcion or '-',
                    },
                    'actividades': contrato.actividades,
                    'unidad_medida': contrato.unidad_medida or '-',
                    'valor_contrato': float(contrato.valor_contrato),
                    'fecha_inicio': contrato.fecha_inicio.strftime('%d/%m/%Y'),
                    'fecha_fin': contrato.fecha_fin.strftime('%d/%m/%Y') if contrato.fecha_fin else '-',
                    'estado': contrato.get_estado_display(),
                    'descripcion': contrato.descripcion or '-',
                    'total_pagado': float(pagado_contrato),
                    'pendiente': float(pendiente_contrato),
                    'porcentaje_avance': round(avance_contrato, 2),
                    'cantidad_pagos': pagos.count(),
                    'pagos': pagos_list,
                })
                
                total_valor += contrato.valor_contrato
                total_pagado += pagado_contrato
            
            data['contratos'] = contratos_list
            data['valor_total_contratos'] = float(total_valor)
            data['total_pagado'] = float(total_pagado)
            data['total_pendiente'] = float(total_valor - total_pagado)
            data['porcentaje_avance'] = round((total_pagado / total_valor * 100) if total_valor > 0 else 0, 2)
            
            # Cantidad total de pagos
            data['cantidad_pagos'] = sum(c['cantidad_pagos'] for c in contratos_list)
            
            # Tipo de cambio para conversiones
            data['tipo_cambio'] = float(tipo_cambio)
            
            return JsonResponse(data)
            
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)


class ContratistaEstadoCuentaAPIView(LoginRequiredMixin, View):
    """
    API para obtener el estado de cuenta de un contratista
    Muestra movimientos cronológicos con saldo acumulado
    """
    
    def get(self, request, pk):
        try:
            contratista = get_object_or_404(Contratista, pk=pk, eliminado=False)
            tipo_cambio = get_tipo_cambio_actual()
            
            # Obtener todos los contratos y pagos
            contratos = ContratoProyecto.objects.filter(
                contratista=contratista,
                eliminado=False
            ).select_related('proyecto').order_by('fecha_inicio')
            
            movimientos = []
            saldo_acumulado = Decimal('0.00')
            
            for contrato in contratos:
                # Agregar contrato como movimiento inicial
                saldo_acumulado += contrato.valor_contrato
                
                movimientos.append({
                    'fecha': contrato.fecha_inicio.strftime('%d/%m/%Y'),
                    'tipo': 'contrato',
                    'descripcion': f'Contrato {contrato.codigo} - {contrato.proyecto.nombre}',
                    'proyecto': contrato.proyecto.nombre,
                    'debe': float(contrato.valor_contrato),
                    'haber': 0,
                    'saldo': float(saldo_acumulado),
                })
                
                # Agregar pagos del contrato
                pagos = PagoContratista.objects.filter(
                    contrato=contrato,
                    eliminado=False,
                    estado='aprobado'
                ).order_by('fecha_pago')
                
                for pago in pagos:
                    saldo_acumulado -= pago.monto_cordobas
                    
                    movimientos.append({
                        'fecha': pago.fecha_pago.strftime('%d/%m/%Y'),
                        'tipo': 'pago',
                        'descripcion': f'Pago {pago.codigo} - {pago.concepto}',
                        'proyecto': contrato.proyecto.nombre,
                        'debe': 0,
                        'haber': float(pago.monto_cordobas),
                        'saldo': float(saldo_acumulado),
                        'forma_pago': pago.get_forma_pago_display(),
                    })
            
            # Ordenar por fecha
            movimientos.sort(key=lambda x: x['fecha'])
            
            # Calcular totales
            total_debe = sum(m['debe'] for m in movimientos)
            total_haber = sum(m['haber'] for m in movimientos)
            
            data = {
                'contratista': {
                    'nombre': contratista.nombre_completo,
                    'cedula': contratista.numero_cedula,
                },
                'movimientos': movimientos,
                'totales': {
                    'debe': total_debe,
                    'haber': total_haber,
                    'saldo': total_debe - total_haber,
                },
                'tipo_cambio': float(tipo_cambio),
            }
            
            return JsonResponse(data)
            
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
        

class ContratoCreateView(LoginRequiredMixin, CreateView):
    model = ContratoProyecto
    form_class = ContratoProyectoForm
    template_name = 'contratistas/contrato_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.proyecto = get_object_or_404(Proyecto, pk=self.kwargs['proyecto_id'], eliminado=False)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        #kwargs['proyecto'] = self.proyecto
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyecto'] = self.proyecto
        context['titulo'] = 'Crear Contrato'
        context['boton'] = 'Crear Contrato'
        return context
    
    def form_valid(self, form):
        form.instance.proyecto = self.proyecto
        form.instance.creado_por = self.request.user
        messages.success(self.request, f'✅ Contrato creado exitosamente')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # ✅ AGREGAR ESTA FUNCIÓN
        print("=" * 50)
        print("ERRORES EN EL FORMULARIO:")
        print(form.errors)
        print("=" * 50)
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('proyecto_detalle', kwargs={'pk': self.proyecto.id})

class ContratoUpdateView(LoginRequiredMixin, UpdateView):
    model = ContratoProyecto
    form_class = ContratoProyectoForm
    template_name = 'contratistas/contrato_form.html'
    
    def get_queryset(self):
        return ContratoProyecto.objects.filter(eliminado=False)
    
    def dispatch(self, request, *args, **kwargs):
        self.proyecto = self.get_object().proyecto
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['proyecto'] = self.proyecto
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #context['proyecto'] = self.proyecto
        context['titulo'] = 'Editar Contrato'
        context['boton'] = 'Guardar Cambios'
        return context
    
    def get_success_url(self):
        return reverse('proyecto_detalle', kwargs={'pk': self.proyecto.id})

class ContratoDeleteView(LoginRequiredMixin, DeleteView):
    model = ContratoProyecto
    
    def post(self, request, *args, **kwargs):
        contrato = self.get_object()
        proyecto_id = contrato.proyecto.id
        contrato.eliminado = True
        contrato.save()
        messages.success(request, f'✅ Contrato eliminado')
        return redirect('proyecto_detalle', pk=proyecto_id)

class ContratistaDetalleView(DetailView):
    """Vista de detalle del contratista con toda su información"""
    model = Contratista
    template_name = 'contratistas/contratista_detalle.html'
    context_object_name = 'contratista'
    
    def get_queryset(self):
        return Contratista.objects.filter(eliminado=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contratista = self.object
        
        # Obtener todos los contratos del contratista
        contratos = ContratoProyecto.objects.filter(
            contratista=contratista,
            eliminado=False
        ).select_related('proyecto').prefetch_related('avaluos')
        
        # Obtener todos los avalúos ordenados por fecha
        todos_avaluos = AvaluoContratista.objects.filter(
            contrato__contratista=contratista,
            contrato__eliminado=False,
            eliminado=False
        ).select_related('contrato', 'contrato__proyecto').order_by('-fecha_pago')
        
        context['contratos'] = contratos
        context['todos_avaluos'] = todos_avaluos
        context['total_avaluos'] = todos_avaluos.count()
        
        return context
    
class PagoContratistaCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo pago a contratista"""
    model = AvaluoContratista
    form_class = PagoContratistaForm
    template_name = 'contratistas/pago_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Obtener el contrato
        self.contrato = get_object_or_404(
            ContratoProyecto,
            pk=self.kwargs['contrato_id'],
            eliminado=False
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['contrato'] = self.contrato
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contrato'] = self.contrato
        context['contratista'] = self.contrato.contratista
        context['proyecto'] = self.contrato.proyecto
        context['titulo'] = 'Registrar Pago'
        context['boton'] = 'Registrar Pago'
        
        contrato = context['contrato']
        if contrato:
            context['contrato'] = contrato
            
            # Calcular total avaluado hasta ahora
            from django.db.models import Sum
            total = contrato.avaluos.filter(eliminado=False).aggregate(
                total=Sum('monto_cordobas')
            )['total'] or 0
            
            context['total_avaluado'] = total
        # Información financiera del contrato
        context['info_financiera'] = {
            'valor_contrato': self.contrato.valor_contrato,
            'total_pagado': self.contrato.total_pagado,
            'pendiente': self.contrato.total_pendiente,
            'porcentaje_avance': self.contrato.porcentaje_avance,
            'cantidad_pagos': self.contrato.cantidad_avaluos,
        }
        
        return context
    
    def form_valid(self, form):
        # Asignar el contrato y el usuario que registra
        form.instance.contrato = self.contrato
        form.instance.ingresado_por = self.request.user
        form.instance.estado = 'pendiente'
        
        messages.success(
            self.request,
            f'✅ Pago registrado exitosamente. Pendiente de aprobación.'
        )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirigir al detalle del contrato
        return reverse('proyecto_detalle', kwargs={'pk': self.contrato.proyecto.id})

class PagoContratistaUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para editar un pago (solo si está pendiente)"""
    model = PagoContratista
    form_class = PagoContratistaForm
    template_name = 'contratistas/pago_form.html'
    
    def get_queryset(self):
        # Solo pagos pendientes pueden editarse
        return PagoContratista.objects.filter(
            eliminado=False,
            estado='pendiente'
        )
    
    def dispatch(self, request, *args, **kwargs):
        pago = self.get_object()
        self.contrato = pago.contrato
        
        # Validar que el pago está en estado pendiente
        if pago.estado != 'pendiente':
            messages.error(
                request,
                '❌ Solo se pueden editar pagos en estado pendiente.'
            )
            return redirect('proyecto_detalle', pk=self.contrato.proyecto.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['contrato'] = self.contrato
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contrato'] = self.contrato
        context['contratista'] = self.contrato.contratista
        context['proyecto'] = self.contrato.proyecto
        context['titulo'] = 'Editar Pago'
        context['boton'] = 'Guardar Cambios'
        
        # Información financiera del contrato
        context['info_financiera'] = {
            'valor_contrato': self.contrato.valor_contrato,
            'total_pagado': self.contrato.total_pagado,
            'pendiente': self.contrato.total_pendiente,
            'porcentaje_avance': self.contrato.porcentaje_avance,
            'cantidad_pagos': self.contrato.cantidad_pagos,
        }
        
        return context
    
    def form_valid(self, form):
        messages.success(
            self.request,
            f'✅ Pago actualizado exitosamente.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('proyecto_detalle', kwargs={'pk': self.contrato.proyecto.id})

class PagoContratistaDeleteView(LoginRequiredMixin, DeleteView):
    """Vista para eliminar un pago (soft delete)"""
    model = PagoContratista
    
    def get_queryset(self):
        # Solo pagos pendientes pueden eliminarse
        return PagoContratista.objects.filter(
            eliminado=False,
            estado='pendiente'
        )
    
    def post(self, request, *args, **kwargs):
        pago = self.get_object()
        
        if pago.estado != 'pendiente':
            messages.error(
                request,
                '❌ Solo se pueden eliminar pagos en estado pendiente.'
            )
        else:
            proyecto_id = pago.contrato.proyecto.id
            pago.eliminado = True
            pago.save()
            messages.success(request, f'✅ Pago eliminado exitosamente')
            return redirect('proyecto_detalle', pk=proyecto_id)
        
        return redirect('proyecto_detalle', pk=pago.contrato.proyecto.id)

class PagoContratistaDetalleView(LoginRequiredMixin, DetailView):
    """Vista de detalle del pago con timeline de aprobaciones"""
    model = PagoContratista
    template_name = 'contratistas/pago_detalle.html'
    context_object_name = 'pago'
    
    def get_queryset(self):
        return PagoContratista.objects.filter(eliminado=False).select_related(
            'contrato__contratista',
            'contrato__proyecto',
            'ingresado_por',
            'aprobado_gerente_por',
            'aprobado_contador_por'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago = self.object
        
        context['contrato'] = pago.contrato
        context['contratista'] = pago.contrato.contratista
        context['proyecto'] = pago.contrato.proyecto
        
        # Timeline de aprobaciones
        timeline = []
        
        # 1. Ingresado
        timeline.append({
            'estado': 'ingresado',
            'titulo': 'Pago Registrado',
            'usuario': pago.ingresado_por,
            'fecha': pago.fecha_ingreso,
            'icono': 'add_circle',
            'color': 'blue',
            'completado': True
        })
        
        # 2. Aprobado Gerente
        if pago.aprobado_gerente_por:
            timeline.append({
                'estado': 'aprobado_gerente',
                'titulo': 'Aprobado por Gerente',
                'usuario': pago.aprobado_gerente_por,
                'fecha': pago.fecha_aprobacion_gerente,
                'icono': 'check_circle',
                'color': 'purple',
                'completado': True
            })
        else:
            timeline.append({
                'estado': 'aprobado_gerente',
                'titulo': 'Pendiente Aprobación Gerente',
                'usuario': None,
                'fecha': None,
                'icono': 'schedule',
                'color': 'gray',
                'completado': False
            })
        
        # 3. Aprobado Contador
        if pago.aprobado_contador_por:
            timeline.append({
                'estado': 'aprobado_contador',
                'titulo': 'Aprobado por Contador',
                'usuario': pago.aprobado_contador_por,
                'fecha': pago.fecha_aprobacion_contador,
                'icono': 'verified',
                'color': 'green',
                'completado': True
            })
        else:
            timeline.append({
                'estado': 'aprobado_contador',
                'titulo': 'Pendiente Aprobación Contador',
                'usuario': None,
                'fecha': None,
                'icono': 'pending',
                'color': 'gray',
                'completado': False
            })
        
        context['timeline'] = timeline
        
        # Verificar permisos del usuario actual
        user = self.request.user
        context['puede_aprobar_gerente'] = (
            pago.estado == 'pendiente' and 
            (user.rol in ['administrador', 'gerente'])
        )
        context['puede_aprobar_contador'] = (
            pago.estado == 'aprobado_gerente' and 
            (user.rol in ['administrador', 'contador'])
        )
        context['puede_rechazar'] = (
            pago.estado in ['pendiente', 'aprobado_gerente'] and
            (user.rol in ['administrador', 'gerente', 'contador'])
        )
        
        return context


class PagoAprobarGerenteView(LoginRequiredMixin, View):
    """Vista para aprobar pago como gerente"""
    
    def post(self, request, *args, **kwargs):
        pago = get_object_or_404(
            PagoContratista,
            pk=kwargs['pk'],
            eliminado=False
        )
        
        # Verificar permisos
        if request.user.rol not in ['administrador', 'gerente']:
            messages.error(
                request,
                '❌ No tienes permisos para aprobar pagos como gerente.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        # Verificar estado
        if pago.estado != 'pendiente':
            messages.error(
                request,
                '❌ Solo se pueden aprobar pagos en estado PENDIENTE.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        try:
            # Aprobar
            pago.aprobar_gerente(request.user)
            
            messages.success(
                request,
                f'✅ Pago {pago.codigo} aprobado como GERENTE. '
                f'Ahora debe ser aprobado por el CONTADOR.'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al aprobar el pago: {str(e)}'
            )
        
        return redirect('pago_detalle', pk=pago.id)


class PagoAprobarContadorView(LoginRequiredMixin, View):
    """Vista para aprobar pago como contador (aprobación final)"""
    
    def post(self, request, *args, **kwargs):
        pago = get_object_or_404(
            PagoContratista,
            pk=kwargs['pk'],
            eliminado=False
        )
        
        # Verificar permisos
        if request.user.rol not in ['administrador', 'contador']:
            messages.error(
                request,
                '❌ No tienes permisos para aprobar pagos como contador.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        # Verificar estado (puede ser pendiente O aprobado_gerente)
        if pago.estado not in ['pendiente', 'aprobado_gerente']:
            messages.error(
                request,
                '❌ Este pago no puede ser aprobado por el contador en su estado actual.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        try:
            # Aprobar
            pago.aprobar_contador(request.user)
            
            messages.success(
                request,
                f'✅ Pago {pago.codigo} APROBADO FINAL. '
                f'El pago ha sido registrado y suma al total del contrato.'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al aprobar el pago: {str(e)}'
            )
        
        return redirect('pago_detalle', pk=pago.id)


class PagoRechazarView(LoginRequiredMixin, View):
    """Vista para rechazar un pago"""
    
    def post(self, request, *args, **kwargs):
        pago = get_object_or_404(
            PagoContratista,
            pk=kwargs['pk'],
            eliminado=False
        )
        
        # Verificar permisos
        if request.user.rol not in ['administrador', 'gerente', 'contador']:
            messages.error(
                request,
                '❌ No tienes permisos para rechazar pagos.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        # Verificar estado
        if pago.estado not in ['pendiente', 'aprobado_gerente']:
            messages.error(
                request,
                '❌ Solo se pueden rechazar pagos pendientes o aprobados por gerente.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        # Obtener motivo del rechazo
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(
                request,
                '❌ Debes proporcionar un motivo para rechazar el pago.'
            )
            return redirect('pago_detalle', pk=pago.id)
        
        try:
            # Rechazar
            pago.rechazar(request.user, motivo)
            
            messages.warning(
                request,
                f'⚠️ Pago {pago.codigo} RECHAZADO. Motivo: {motivo}'
            )
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al rechazar el pago: {str(e)}'
            )
        
        return redirect('pago_detalle', pk=pago.id)


class PagosPendientesListView(LoginRequiredMixin, ListView):
    """Vista de lista de pagos pendientes de aprobación"""
    model = PagoContratista
    template_name = 'contratistas/pagos_pendientes.html'
    context_object_name = 'pagos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PagoContratista.objects.filter(
            eliminado=False
        ).exclude(
            estado='aprobado'
        ).select_related(
            'contrato__contratista',
            'contrato__proyecto',
            'ingresado_por'
        ).order_by('-fecha_ingreso')
        
        # Filtro por estado
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtro por contratista
        contratista_id = self.request.GET.get('contratista', '').strip()
        if contratista_id:
            queryset = queryset.filter(contrato__contratista_id=contratista_id)
        
        # Filtro por proyecto
        proyecto_id = self.request.GET.get('proyecto', '').strip()
        if proyecto_id:
            queryset = queryset.filter(contrato__proyecto_id=proyecto_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        total_pendientes = PagoContratista.objects.filter(
            eliminado=False,
            estado='pendiente'
        ).count()
        
        total_aprobados_gerente = PagoContratista.objects.filter(
            eliminado=False,
            estado='aprobado_gerente'
        ).count()
        
        total_rechazados = PagoContratista.objects.filter(
            eliminado=False,
            estado='rechazado'
        ).count()
        
        context['stats'] = {
            'total_pendientes': total_pendientes,
            'total_aprobados_gerente': total_aprobados_gerente,
            'total_rechazados': total_rechazados,
        }
        
        # Listas para filtros
        context['contratistas'] = Contratista.objects.filter(eliminado=False).order_by('apellido', 'nombre')
        context['proyectos'] = Proyecto.objects.filter(eliminado=False).order_by('nombre')
        context['estados'] = PagoContratista.ESTADO_CHOICES
        
        # Parámetros actuales
        context['estado_seleccionado'] = self.request.GET.get('estado', '')
        context['contratista_seleccionado'] = self.request.GET.get('contratista', '')
        context['proyecto_seleccionado'] = self.request.GET.get('proyecto', '')
        
        return context
