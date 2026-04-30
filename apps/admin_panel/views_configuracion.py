"""
Vista de Configuración del Sistema
apps/admin_panel/views_configuracion.py
"""
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json

from apps.planillas.models import DiaFeriado, TipoCambio
from apps.core.puestos_data import PUESTOS_DATA
from apps.proyectos.models import Proyecto


class ConfiguracionView(LoginRequiredMixin, View):
    """Vista principal de configuración del sistema"""
    template_name = 'admin_panel/configuracion/index.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Solo admin y gerente_general
        rc = getattr(request.user, 'rol_codigo', '')
        if not (request.user.is_superuser or rc in ['admin', 'gerente_general']):
            messages.error(request, 'No tiene permisos para acceder a la configuración.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        # Feriados del año actual y siguiente
        anio_actual = timezone.localdate().year
        feriados_raw = DiaFeriado.objects.filter(
            fecha__year__gte=anio_actual,
            activo=True
        ).select_related('proyecto').order_by('fecha')
        
        # Agrupar por fecha+descripción
        from collections import OrderedDict
        feriados_agrupados = OrderedDict()
        for f in feriados_raw:
            clave = (f.fecha, f.descripcion)
            if clave not in feriados_agrupados:
                feriados_agrupados[clave] = {
                    'fecha': f.fecha,
                    'descripcion': f.descripcion,
                    'tipo': f.tipo,
                    'proyectos': [],
                    'ids': [],
                }
            if f.tipo == 'proyecto' and f.proyecto:
                feriados_agrupados[clave]['proyectos'].append(f.proyecto.nombre)
            feriados_agrupados[clave]['ids'].append(f.id)
        feriados = list(feriados_agrupados.values())
        
        feriados_inactivos_raw = DiaFeriado.objects.filter(
            fecha__year__gte=anio_actual,
            activo=False
        ).select_related('proyecto').order_by('fecha')
        
        feriados_inactivos_agrupados = OrderedDict()
        for f in feriados_inactivos_raw:
            clave = (f.fecha, f.descripcion)
            if clave not in feriados_inactivos_agrupados:
                feriados_inactivos_agrupados[clave] = {
                    'fecha': f.fecha,
                    'descripcion': f.descripcion,
                    'tipo': f.tipo,
                    'proyectos': [],
                    'ids': [],
                }
            if f.tipo == 'proyecto' and f.proyecto:
                feriados_inactivos_agrupados[clave]['proyectos'].append(f.proyecto.nombre)
            feriados_inactivos_agrupados[clave]['ids'].append(f.id)
        feriados_inactivos = list(feriados_inactivos_agrupados.values())
        
        # Tipo de cambio
        tipo_cambio = TipoCambio.get_actual()
        historial_tc = TipoCambio.objects.order_by('-fecha')[:10]
        
        # Puestos y áreas
        puestos_data = PUESTOS_DATA
        
        # Proyectos para feriados específicos
        proyectos = Proyecto.objects.filter(eliminado=False).order_by('nombre')
        
        context = {
            'feriados': feriados,
            'feriados_inactivos': feriados_inactivos,
            'tipo_cambio': tipo_cambio,
            'historial_tc': historial_tc,
            'puestos_data': puestos_data,
            'anio_actual': anio_actual,
            'proyectos': proyectos,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        accion = request.POST.get('accion')
        
        if accion == 'agregar_feriado':
            return self._agregar_feriado(request)
        elif accion == 'eliminar_feriado':
            return self._eliminar_feriado(request)
        elif accion == 'toggle_feriado':
            return self._toggle_feriado(request)
        elif accion == 'actualizar_tipo_cambio':
            return self._actualizar_tipo_cambio(request)
        elif accion == 'agregar_puesto':
            return self._agregar_puesto(request)
        elif accion == 'eliminar_puesto':
            return self._eliminar_puesto(request)
        elif accion == 'agregar_area':
            return self._agregar_area(request)
        elif accion == 'eliminar_area':
            return self._eliminar_area(request)
        
        return redirect('admin_panel:configuracion')
    
    def _agregar_feriado(self, request):
        fecha = request.POST.get('fecha')
        descripcion = request.POST.get('descripcion', '').strip()
        tipo = request.POST.get('tipo', 'nacional')
        
        if not fecha or not descripcion:
            messages.error(request, 'Fecha y descripción son obligatorias.')
            return redirect('admin_panel:configuracion')
        
        from datetime import datetime
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        
        if tipo == 'nacional':
            if DiaFeriado.objects.filter(fecha=fecha_obj, tipo='nacional', activo=True).exists():
                messages.warning(request, f'Ya existe un feriado nacional para el {fecha_obj.strftime("%d/%m/%Y")}.')
                return redirect('admin_panel:configuracion')
            
            DiaFeriado.objects.create(
                fecha=fecha_obj,
                descripcion=descripcion,
                tipo='nacional',
                activo=True
            )
            messages.success(request, f'Feriado nacional "{descripcion}" agregado para el {fecha_obj.strftime("%d/%m/%Y")}.')
        else:
            from apps.proyectos.models import Proyecto
            proyecto_ids = request.POST.getlist('proyecto_ids')
            
            if not proyecto_ids:
                messages.error(request, 'Debe seleccionar al menos un proyecto.')
                return redirect('admin_panel:configuracion')
            
            creados = 0
            duplicados = 0
            for pid in proyecto_ids:
                proyecto = Proyecto.objects.filter(id=pid, eliminado=False).first()
                if not proyecto:
                    continue
                if DiaFeriado.objects.filter(fecha=fecha_obj, tipo='proyecto', proyecto=proyecto, activo=True).exists():
                    duplicados += 1
                    continue
                DiaFeriado.objects.create(
                    fecha=fecha_obj,
                    descripcion=descripcion,
                    tipo='proyecto',
                    proyecto=proyecto,
                    activo=True
                )
                creados += 1
            
            msg = f'Feriado "{descripcion}" agregado para {creados} proyecto(s).'
            if duplicados > 0:
                msg += f' {duplicados} ya existían.'
            messages.success(request, msg)
        
        return redirect('admin_panel:configuracion')

    def _eliminar_feriado(self, request):
        feriado_ids = request.POST.get('feriado_ids', '')
        ids = [int(x) for x in feriado_ids.split(',') if x.strip()]
        if ids:
            count = DiaFeriado.objects.filter(id__in=ids).count()
            DiaFeriado.objects.filter(id__in=ids).delete()
            messages.success(request, f'Feriado eliminado ({count} registros).')
        else:
            messages.error(request, 'Feriado no encontrado.')
        return redirect('admin_panel:configuracion')
    
    def _toggle_feriado(self, request):
        feriado_ids = request.POST.get('feriado_ids', '')
        ids = [int(x) for x in feriado_ids.split(',') if x.strip()]
        if ids:
            feriados = DiaFeriado.objects.filter(id__in=ids)
            if feriados.exists():
                nuevo_estado = not feriados.first().activo
                feriados.update(activo=nuevo_estado)
                estado = 'activado' if nuevo_estado else 'desactivado'
                messages.success(request, f'Feriado {estado} ({len(ids)} registros).')
            else:
                messages.error(request, 'Feriado no encontrado.')
        return redirect('admin_panel:configuracion')
    
    def _actualizar_tipo_cambio(self, request):
        valor = request.POST.get('valor', '').strip()
        if not valor:
            messages.error(request, 'El valor del tipo de cambio es obligatorio.')
            return redirect('admin_panel:configuracion')
        
        try:
            valor_decimal = Decimal(valor.replace(',', '.'))
            if valor_decimal <= 0:
                raise ValueError
        except:
            messages.error(request, 'Valor inválido para el tipo de cambio.')
            return redirect('admin_panel:configuracion')
        
        # Desactivar todos los anteriores
        TipoCambio.objects.filter(activo=True).update(activo=False)
        
        # Crear nuevo
        TipoCambio.objects.create(
            valor=valor_decimal,
            activo=True,
            fecha=timezone.localdate(),
            modificado_por=request.user
        )
        messages.success(request, f'Tipo de cambio actualizado a C$ {valor_decimal}')
        return redirect('admin_panel:configuracion')
    
    def _agregar_puesto(self, request):
        area = request.POST.get('area', '').strip()
        puesto = request.POST.get('puesto', '').strip()
        
        if not area or not puesto:
            messages.error(request, 'Área y puesto son obligatorios.')
            return redirect('admin_panel:configuracion')
        
        if area in PUESTOS_DATA:
            if puesto not in PUESTOS_DATA[area]:
                PUESTOS_DATA[area].append(puesto)
                self._guardar_puestos_data()
                messages.success(request, f'Puesto "{puesto}" agregado al área "{area}".')
            else:
                messages.warning(request, f'El puesto "{puesto}" ya existe en "{area}".')
        else:
            messages.error(request, f'Área "{area}" no encontrada.')
        return redirect('admin_panel:configuracion')
    
    def _eliminar_puesto(self, request):
        area = request.POST.get('area', '').strip()
        puesto = request.POST.get('puesto', '').strip()
        
        if area in PUESTOS_DATA and puesto in PUESTOS_DATA[area]:
            PUESTOS_DATA[area].remove(puesto)
            self._guardar_puestos_data()
            messages.success(request, f'Puesto "{puesto}" eliminado del área "{area}".')
        else:
            messages.error(request, 'Puesto no encontrado.')
        return redirect('admin_panel:configuracion')
    
    def _agregar_area(self, request):
        area = request.POST.get('area', '').strip()
        if not area:
            messages.error(request, 'El nombre del área es obligatorio.')
            return redirect('admin_panel:configuracion')
        
        if area not in PUESTOS_DATA:
            PUESTOS_DATA[area] = []
            self._guardar_puestos_data()
            messages.success(request, f'Área "{area}" creada.')
        else:
            messages.warning(request, f'El área "{area}" ya existe.')
        return redirect('admin_panel:configuracion')
    
    def _eliminar_area(self, request):
        area = request.POST.get('area', '').strip()
        if area in PUESTOS_DATA:
            if len(PUESTOS_DATA[area]) > 0:
                messages.error(request, f'No se puede eliminar el área "{area}" porque tiene puestos asignados. Elimine los puestos primero.')
            else:
                del PUESTOS_DATA[area]
                self._guardar_puestos_data()
                messages.success(request, f'Área "{area}" eliminada.')
        else:
            messages.error(request, 'Área no encontrada.')
        return redirect('admin_panel:configuracion')
    
    def _guardar_puestos_data(self):
        """Reescribe el archivo puestos_data.py con los datos actualizados"""
        import os
        from django.conf import settings
        
        filepath = os.path.join(settings.BASE_DIR, 'apps', 'core', 'puestos_data.py')
        
        lines = ['"""\nDatos de Puestos Laborales y Áreas de Trabajo\napps/core/puestos_data.py\n"""\n\n']
        lines.append('# Diccionario con áreas de trabajo y sus puestos laborales\n')
        lines.append('PUESTOS_DATA = {\n')
        for area, puestos in PUESTOS_DATA.items():
            puestos_str = ', '.join([f"'{p}'" for p in sorted(puestos)])
            lines.append(f"    '{area}': [{puestos_str}],\n")
        lines.append('}\n\n')
        
        # Regenerar las constantes derivadas
        lines.append('# Lista de áreas de trabajo ordenadas\n')
        lines.append('AREAS_TRABAJO = list(PUESTOS_DATA.keys())\n\n')
        lines.append("AREA_TRABAJO_CHOICES = [('', 'Seleccione un área')] + [(a, a) for a in AREAS_TRABAJO]\n\n")
        lines.append('TODOS_PUESTOS = []\n')
        lines.append('for puestos in PUESTOS_DATA.values():\n')
        lines.append('    TODOS_PUESTOS.extend(puestos)\n')
        lines.append('TODOS_PUESTOS = sorted(set(TODOS_PUESTOS))\n\n')
        lines.append("PUESTO_LABORAL_CHOICES = [('', 'Seleccione un puesto')] + [(p, p) for p in TODOS_PUESTOS]\n\n")
        
        # Funciones auxiliares
        lines.append('def get_puestos(area_trabajo):\n')
        lines.append('    puestos = PUESTOS_DATA.get(area_trabajo, [])\n')
        lines.append('    return sorted(puestos)\n\n')
        lines.append('def get_puesto_choices(area_trabajo):\n')
        lines.append('    puestos = get_puestos(area_trabajo)\n')
        lines.append("    return [('', 'Seleccione un puesto')] + [(p, p) for p in puestos]\n\n")
        lines.append('def get_all_puesto_choices():\n')
        lines.append('    return PUESTO_LABORAL_CHOICES\n\n')
        lines.append('def get_area_por_puesto(puesto):\n')
        lines.append('    for area, puestos in PUESTOS_DATA.items():\n')
        lines.append('        if puesto in puestos:\n')
        lines.append('            return area\n')
        lines.append('    return None\n\n')
        lines.append('def validar_area_puesto(area_trabajo, puesto_laboral):\n')
        lines.append('    if not area_trabajo or not puesto_laboral:\n')
        lines.append('        return True\n')
        lines.append('    puestos = PUESTOS_DATA.get(area_trabajo, [])\n')
        lines.append('    return puesto_laboral in puestos\n')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            