"""
Formularios para el módulo de Contratistas
apps/contratistas/forms.py
"""
from django import forms
from django.core.validators import RegexValidator
from .models import Contratista, ContratoProyecto
from apps.proyectos.models import Proyecto


class ContratistaForm(forms.ModelForm):
    """Formulario para crear/editar contratista"""
    
    # Validador de cédula
    cedula_validator = RegexValidator(
        regex=r'^\d{13}[A-Z]$',
        message='La cédula debe tener 13 dígitos seguidos de una letra mayúscula. Ejemplo: 0011234567890A'
    )
    
    # Validador de teléfono
    telefono_validator = RegexValidator(
        regex=r'^\d{8}$',
        message='El teléfono debe tener exactamente 8 dígitos'
    )
    
    # Override de campos para agregar validadores y widgets personalizados
    numero_cedula = forms.CharField(
        max_length=20,
        validators=[cedula_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0011234567890A',
            'maxlength': '14'
        }),
        label='Número de Cédula',
        help_text='13 dígitos + 1 letra mayúscula'
    )
    
    telefono = forms.CharField(
        max_length=8,
        validators=[telefono_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '88887777',
            'maxlength': '8'
        }),
        label='Teléfono'
    )
    
    # Campo para seleccionar múltiples proyectos
    proyectos_asignados = forms.ModelMultipleChoiceField(
        queryset=Proyecto.objects.filter(eliminado=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Proyectos Asignados',
        help_text='Selecciona uno o más proyectos donde trabaja este contratista'
    )
    
    class Meta:
        model = Contratista
        fields = [
            'nombre',
            'apellido',
            'numero_cedula',
            'foto_cedula',
            'telefono',
            'email',
            'direccion',
            'departamento',
            'municipio',
            'banco',
            'numero_cuenta',
            'tipo_cuenta',
            'moneda_cuenta',
            'activo',
        ]
        
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el apellido'
            }),
            'foto_cedula': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'municipio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Municipio'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
            'numero_cuenta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta bancaria'
            }),
            'tipo_cuenta': forms.Select(attrs={
                'class': 'form-control'
            }),
            'moneda_cuenta': forms.Select(attrs={
                'class': 'form-control'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'foto_cedula': 'Foto de Cédula',
            'telefono': 'Teléfono',
            'email': 'Correo Electrónico',
            'direccion': 'Dirección',
            'departamento': 'Departamento',
            'municipio': 'Municipio',
            'banco': 'Banco',
            'numero_cuenta': 'Número de Cuenta',
            'tipo_cuenta': 'Tipo de Cuenta',
            'moneda_cuenta': 'Moneda',
            'activo': 'Contratista Activo',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Opciones de departamentos de Nicaragua
        departamentos = [
            ('Boaco', 'Boaco'),
            ('Carazo', 'Carazo'),
            ('Chinandega', 'Chinandega'),
            ('Chontales', 'Chontales'),
            ('Costa Caribe Norte', 'Costa Caribe Norte'),
            ('Costa Caribe Sur', 'Costa Caribe Sur'),
            ('Estelí', 'Estelí'),
            ('Granada', 'Granada'),
            ('Jinotega', 'Jinotega'),
            ('León', 'León'),
            ('Madriz', 'Madriz'),
            ('Managua', 'Managua'),
            ('Masaya', 'Masaya'),
            ('Matagalpa', 'Matagalpa'),
            ('Nueva Segovia', 'Nueva Segovia'),
            ('Río San Juan', 'Río San Juan'),
            ('Rivas', 'Rivas'),
        ]
        
        self.fields['departamento'].widget.choices = [('', '-- Seleccione --')] + departamentos
        
        # Si estamos editando, cargar los proyectos actuales
        if self.instance and self.instance.pk:
            # Obtener los proyectos a través de los contratos existentes
            proyectos_ids = ContratoProyecto.objects.filter(
                contratista=self.instance,
                eliminado=False
            ).values_list('proyecto_id', flat=True).distinct()
            
            self.fields['proyectos_asignados'].initial = proyectos_ids
    
    def clean_numero_cedula(self):
        """Validar que la cédula sea única"""
        cedula = self.cleaned_data.get('numero_cedula')
        
        # Si estamos editando, excluir el contratista actual de la validación
        qs = Contratista.objects.filter(numero_cedula=cedula, eliminado=False)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Ya existe un contratista con esta cédula.')
        
        return cedula
    
    def clean_email(self):
        """Validar y limpiar el email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        return email
    
    def save(self, commit=True):
        """Guardar el contratista y sus proyectos"""
        contratista = super().save(commit=False)
        
        if commit:
            contratista.save()
            
            # Guardar los proyectos asignados
            # Nota: Los contratos se crearán después en otro paso
            # Aquí solo guardamos la relación many-to-many si existe
            if 'proyectos_asignados' in self.cleaned_data:
                # Esta relación se manejará con contratos, no directamente
                pass
        
        return contratista
    

class ContratoProyectoForm(forms.ModelForm):
    """Formulario para crear y editar contratos de proyectos"""
    
    class Meta:
        model = ContratoProyecto
        fields = [
            'contratista', 'descripcion', 'actividades',
            'valor_contrato', 'fecha_inicio', 'fecha_fin', 'estado',
        ]
        widgets = {
            'contratista': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'actividades': forms.TextInput(attrs={'class': 'form-input'}),
            'valor_contrato': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, proyecto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if proyecto:
            self.fields['contratista'].queryset = proyecto.contratistas.filter(
                eliminado=False, activo=True
            )
