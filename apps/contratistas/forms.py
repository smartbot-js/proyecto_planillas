"""
Formularios del módulo de Contratistas - ACTUALIZADO PARA AVALÚOS
apps/contratistas/forms.py
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from .models import Contratista, ContratoProyecto, AvaluoContratista
from apps.core.utils import get_tipo_cambio_actual
from apps.core.nicaragua_data import DEPARTAMENTO_CHOICES, get_all_municipio_choices


class ContratistaForm(forms.ModelForm):
    """Formulario para crear/editar contratistas"""
    
    class Meta:
        model = Contratista
        fields = [
            'nombre', 'apellido', 'numero_cedula', 'foto_cedula',
            'telefono', 'email', 'direccion', 'departamento', 'municipio',
            'banco', 'numero_cuenta', 'tipo_cuenta', 'moneda_cuenta'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '001-DDMMYY-0000X'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+505 8888-8888'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            #'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            #'municipio': forms.TextInput(attrs={'class': 'form-control'}),
            'departamento': forms.Select(choices=DEPARTAMENTO_CHOICES, attrs={'class': 'form-control', 'id': 'id_departamento'}),
            'municipio': forms.Select(choices=get_all_municipio_choices(), attrs={'class': 'form-control', 'id': 'id_municipio'}),
            'banco': forms.Select(choices=[
                ('', 'Seleccione un banco'),
                ('BAC', 'BAC'),
                ('BANPRO', 'BANPRO'),
                ('LAFISE', 'LAFISE'),
                ('AVANZ', 'AVANZ'),
                ('BDF', 'BDF'),
                ('FICOHSA', 'FICOHSA'),
                ('PRODUZCAMOS', 'PRODUZCAMOS'),
                ('ATLANTIDA', 'ATLANTIDA'),
            ], attrs={'class': 'form-control'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_cuenta': forms.Select(attrs={'class': 'form-control'}),
            'moneda_cuenta': forms.Select(attrs={'class': 'form-control'}),
        }


class ContratoProyectoForm(forms.ModelForm):
    """Formulario para crear/editar contratos"""
    
    class Meta:
        model = ContratoProyecto
        fields = [
            'contratista', 'descripcion', 'actividades',
             'valor_contrato', 'fecha_inicio', 'fecha_fin', 'estado'
        ]
        widgets = {
            'contratista': forms.Select(attrs={'class': 'form-control'}),
            #'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actividades': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            #'unidad_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'm², ml, unidad, etc.'}),
            'valor_contrato': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que las fechas usen el formato correcto para input type="date"
        self.fields['fecha_inicio'].input_formats = ['%Y-%m-%d']
        self.fields['fecha_fin'].input_formats = ['%Y-%m-%d']


class AvaluoContratistaForm(forms.ModelForm):
    """
    Formulario para registrar avalúos de contratistas
    Incluye campos de período y porcentaje de avance
    """
    
    class Meta:
        model = AvaluoContratista
        fields = [
            'periodo_inicio',
            'periodo_fin',
            'porcentaje_avance',
            'fecha_pago',
            'concepto',
            'monto_cordobas',
            'tipo_cambio',
            'forma_pago',
            'archivo_soporte',
            'observaciones'
        ]
        widgets = {
            'periodo_inicio': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                    'required': True
                }
            ),
            'periodo_fin': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                    'required': True
                }
            ),
            'porcentaje_avance': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'max': '100',
                    'placeholder': 'Calculado automáticamente',
                    'readonly': 'readonly',  # SOLO LECTURA
                    'style': 'background-color: #f3f4f6; cursor: not-allowed;'
                }
            ),
            'fecha_pago': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'concepto': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descripción del trabajo realizado en este período...'
                }
            ),
            'monto_cordobas': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0.01'
                }
            ),
            'tipo_cambio': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.0001',
                    'readonly': 'readonly'
                }
            ),
            'forma_pago': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'archivo_soporte': forms.FileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.pdf,.jpg,.jpeg,.png'
                }
            ),
            'observaciones': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Observaciones adicionales (opcional)...'
                }
            ),
        }
        labels = {
            'periodo_inicio': 'Fecha Inicio del Período',
            'periodo_fin': 'Fecha Fin del Período',
            'porcentaje_avance': '% de Avance Acumulado',
            'fecha_pago': 'Fecha de Registro',
            'concepto': 'Descripción del Trabajo',
            'monto_cordobas': 'Monto en Córdobas',
            'tipo_cambio': 'Tipo de Cambio (C$/USD)',
            'forma_pago': 'Forma de Pago',
            'archivo_soporte': 'Archivo Soporte (Opcional)',
            'observaciones': 'Observaciones',
        }
    
    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        
        # Pre-llenar tipo de cambio
        if not self.instance.pk:
            self.initial['tipo_cambio'] = get_tipo_cambio_actual()
        
        # Si hay contrato, calcular y pre-llenar el porcentaje de avance automáticamente
        if self.contrato:
            # Calcular el último porcentaje de avance aprobado/pagado
            ultimo_avaluo = self.contrato.avaluos.filter(
                eliminado=False,
                estado__in=['aprobado_contador', 'pagado']
            ).order_by('-porcentaje_avance').first()
            
            # Calcular el total avaluado hasta ahora (incluyendo pendientes)
            if not self.instance.pk:  # Solo si es un nuevo avalúo
                avaluos_existentes = self.contrato.avaluos.filter(eliminado=False)
                suma_avaluos = avaluos_existentes.aggregate(
                    total=Sum('monto_cordobas')
                )['total'] or Decimal('0')
                
                # Calcular porcentaje automático
                valor_contrato = self.contrato.valor_contrato
                if valor_contrato > 0:
                    porcentaje_calculado = (suma_avaluos / valor_contrato) * 100
                    
                    # Pre-llenar el campo con el porcentaje calculado
                    self.initial['porcentaje_avance'] = round(porcentaje_calculado, 2)
                    
                    # Actualizar el help text
                    self.fields['porcentaje_avance'].help_text = (
                        f'Calculado automáticamente: {porcentaje_calculado:.2f}% '
                        f'(Total avaluado: C$ {suma_avaluos:,.2f} de C$ {valor_contrato:,.2f}). '
                        f'Puedes ajustarlo manualmente si es necesario.'
                    )
            
            # Si estamos editando, mostrar info del último avance
            elif ultimo_avaluo:
                self.fields['porcentaje_avance'].help_text = f'Último avance registrado: {ultimo_avaluo.porcentaje_avance}%'
                
    def clean_periodo_inicio(self):
        """Validar fecha de inicio del período"""
        periodo_inicio = self.cleaned_data.get('periodo_inicio')
        
        if not periodo_inicio:
            raise ValidationError('La fecha de inicio del período es obligatoria.')
        
        return periodo_inicio
    
    def clean_periodo_fin(self):
        """Validar fecha de fin del período"""
        periodo_inicio = self.cleaned_data.get('periodo_inicio')
        periodo_fin = self.cleaned_data.get('periodo_fin')
        
        if not periodo_fin:
            raise ValidationError('La fecha de fin del período es obligatoria.')
        
        if periodo_inicio and periodo_fin < periodo_inicio:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        
        return periodo_fin
    
    def clean_porcentaje_avance(self):
        """
        Calcular porcentaje de avance automáticamente basado en el monto
        No permitir que el usuario lo modifique manualmente
        """
        # Ignorar lo que el usuario haya puesto
        # y calcular automáticamente
        
        if self.contrato:
            monto_actual = self.cleaned_data.get('monto_cordobas', Decimal('0'))
            
            # Calcular suma de avalúos existentes
            avaluos_existentes = self.contrato.avaluos.filter(eliminado=False)
            
            # Si estamos editando, excluir el avalúo actual
            if self.instance.pk:
                avaluos_existentes = avaluos_existentes.exclude(pk=self.instance.pk)
            
            suma_avaluos = avaluos_existentes.aggregate(
                total=Sum('monto_cordobas')
            )['total'] or Decimal('0')
            
            # Calcular total con el nuevo avalúo
            total_con_nuevo = suma_avaluos + monto_actual
            
            # Calcular porcentaje
            valor_contrato = self.contrato.valor_contrato
            if valor_contrato > 0:
                porcentaje_calculado = (total_con_nuevo / valor_contrato) * 100
                return round(porcentaje_calculado, 2)
            
            return Decimal('0')
        
        # Si no hay contrato, retornar lo que venga
        return self.cleaned_data.get('porcentaje_avance', Decimal('0')) 
    
    def clean_fecha_pago(self):
        """Validar fecha de pago"""
        fecha = self.cleaned_data.get('fecha_pago')
        
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha de pago no puede ser futura.')
        
        return fecha
    
    def clean_monto_cordobas(self):
        """
        Validar monto en córdobas
        - No debe ser negativo o cero
        - La suma de TODOS los avalúos (incluido el actual) no debe exceder el valor del contrato
        """
        monto = self.cleaned_data.get('monto_cordobas')
        
        if monto and monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        
        if self.contrato and monto:
            # Calcular la suma de TODOS los avalúos (pendientes, aprobados, pagados)
            # excluyendo el avalúo actual si estamos editando
            avaluos_existentes = self.contrato.avaluos.filter(eliminado=False)
            
            # Si estamos editando, excluir el avalúo actual del cálculo
            if self.instance.pk:
                avaluos_existentes = avaluos_existentes.exclude(pk=self.instance.pk)
            
            # Sumar todos los montos
            suma_avaluos = avaluos_existentes.aggregate(
                total=Sum('monto_cordobas')
            )['total'] or Decimal('0')
            
            # Sumar el monto actual
            total_con_nuevo = suma_avaluos + monto
            
            # Validar contra el valor total del contrato
            valor_contrato = self.contrato.valor_contrato
            
            if total_con_nuevo > valor_contrato:
                # Calcular cuánto falta
                disponible = valor_contrato - suma_avaluos
                
                raise ValidationError(
                    f'El monto de este avalúo (C$ {monto:,.2f}) excede el límite del contrato. '
                    f'Valor del contrato: C$ {valor_contrato:,.2f} | '
                    f'Ya avaluado: C$ {suma_avaluos:,.2f} | '
                    f'Disponible: C$ {disponible:,.2f}. '
                    f'Si necesitas avaluar más, debes crear un nuevo contrato o modificar el valor del contrato actual.'
                )
        
        return monto
    
    def clean_tipo_cambio(self):
        """Validar tipo de cambio"""
        tipo_cambio = self.cleaned_data.get('tipo_cambio')
        
        if tipo_cambio and tipo_cambio <= 0:
            raise ValidationError('El tipo de cambio debe ser mayor a cero.')
        
        return tipo_cambio
    
    def clean_archivo_soporte(self):
        """Validar archivo soporte"""
        archivo = self.cleaned_data.get('archivo_soporte')
        
        if archivo:
            # Validar tamaño (máximo 10MB)
            if archivo.size > 10 * 1024 * 1024:
                raise ValidationError('El archivo no puede superar los 10MB.')
        
        return archivo


# Alias para mantener compatibilidad con código existente
PagoContratistaForm = AvaluoContratistaForm