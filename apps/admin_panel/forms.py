from django import forms
from .models import Rol
from apps.usuarios.models import Usuario
from django.utils.text import slugify

class RolForm(forms.ModelForm):
    """Formulario para crear/editar roles"""
    
    # Proyectos
    proyectos_ver = forms.BooleanField(required=False, label='Ver proyectos')
    proyectos_crear = forms.BooleanField(required=False, label='Crear proyectos')
    proyectos_editar = forms.BooleanField(required=False, label='Editar proyectos')
    proyectos_eliminar = forms.BooleanField(required=False, label='Eliminar proyectos')
    
    # Trabajadores
    trabajadores_ver = forms.BooleanField(required=False, label='Ver trabajadores')
    trabajadores_crear = forms.BooleanField(required=False, label='Crear trabajadores')
    trabajadores_editar = forms.BooleanField(required=False, label='Editar trabajadores')
    trabajadores_eliminar = forms.BooleanField(required=False, label='Eliminar trabajadores')
    
    # Asistencias
    asistencias_ver = forms.BooleanField(required=False, label='Ver asistencias')
    asistencias_crear = forms.BooleanField(required=False, label='Crear asistencias')
    asistencias_validar = forms.BooleanField(required=False, label='Validar asistencias')
    asistencias_corregir = forms.BooleanField(required=False, label='Corregir asistencias')
    
    # Planillas
    planillas_ver = forms.BooleanField(required=False, label='Ver planillas')
    planillas_crear = forms.BooleanField(required=False, label='Crear planillas')
    planillas_aprobar_gerente = forms.BooleanField(required=False, label='Aprobar (Gerente)')
    planillas_aprobar_contador = forms.BooleanField(required=False, label='Aprobar (Contador)')
    
    # Contratistas
    contratistas_ver = forms.BooleanField(required=False, label='Ver contratistas')
    contratistas_crear = forms.BooleanField(required=False, label='Crear contratistas')
    contratistas_editar = forms.BooleanField(required=False, label='Editar contratistas')
    contratistas_eliminar = forms.BooleanField(required=False, label='Eliminar contratistas')
    
    # Reportes
    reportes_ver = forms.BooleanField(required=False, label='Ver reportes')
    reportes_exportar = forms.BooleanField(required=False, label='Exportar reportes')
    
    # Admin Panel
    admin_panel_acceso = forms.BooleanField(required=False, label='Acceso al panel de administración')
    
    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion', 'alcance_proyectos', 'solo_app_movil', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'alcance_proyectos': forms.Select(attrs={'class': 'form-control'}),
            'solo_app_movil': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            permisos = self.instance.permisos
            
            # Proyectos
            self.fields['proyectos_ver'].initial = permisos.get('proyectos', {}).get('ver', False)
            self.fields['proyectos_crear'].initial = permisos.get('proyectos', {}).get('crear', False)
            self.fields['proyectos_editar'].initial = permisos.get('proyectos', {}).get('editar', False)
            self.fields['proyectos_eliminar'].initial = permisos.get('proyectos', {}).get('eliminar', False)
            
            # Trabajadores
            self.fields['trabajadores_ver'].initial = permisos.get('trabajadores', {}).get('ver', False)
            self.fields['trabajadores_crear'].initial = permisos.get('trabajadores', {}).get('crear', False)
            self.fields['trabajadores_editar'].initial = permisos.get('trabajadores', {}).get('editar', False)
            self.fields['trabajadores_eliminar'].initial = permisos.get('trabajadores', {}).get('eliminar', False)
            
            # Asistencias
            self.fields['asistencias_ver'].initial = permisos.get('asistencias', {}).get('ver', False)
            self.fields['asistencias_crear'].initial = permisos.get('asistencias', {}).get('crear', False)
            self.fields['asistencias_validar'].initial = permisos.get('asistencias', {}).get('validar', False)
            self.fields['asistencias_corregir'].initial = permisos.get('asistencias', {}).get('corregir', False)
            
            # Planillas
            self.fields['planillas_ver'].initial = permisos.get('planillas', {}).get('ver', False)
            self.fields['planillas_crear'].initial = permisos.get('planillas', {}).get('crear', False)
            self.fields['planillas_aprobar_gerente'].initial = permisos.get('planillas', {}).get('aprobar_gerente', False)
            self.fields['planillas_aprobar_contador'].initial = permisos.get('planillas', {}).get('aprobar_contador', False)
            
            # Contratistas
            self.fields['contratistas_ver'].initial = permisos.get('contratistas', {}).get('ver', False)
            self.fields['contratistas_crear'].initial = permisos.get('contratistas', {}).get('crear', False)
            self.fields['contratistas_editar'].initial = permisos.get('contratistas', {}).get('editar', False)
            self.fields['contratistas_eliminar'].initial = permisos.get('contratistas', {}).get('eliminar', False)
            
            # Reportes
            self.fields['reportes_ver'].initial = permisos.get('reportes', {}).get('ver', False)
            self.fields['reportes_exportar'].initial = permisos.get('reportes', {}).get('exportar', False)
            
            # Admin Panel
            self.fields['admin_panel_acceso'].initial = permisos.get('admin_panel', {}).get('acceso', False)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Construir JSON de permisos
        instance.permisos = {
            'proyectos': {
                'ver': self.cleaned_data.get('proyectos_ver', False),
                'crear': self.cleaned_data.get('proyectos_crear', False),
                'editar': self.cleaned_data.get('proyectos_editar', False),
                'eliminar': self.cleaned_data.get('proyectos_eliminar', False),
            },
            'trabajadores': {
                'ver': self.cleaned_data.get('trabajadores_ver', False),
                'crear': self.cleaned_data.get('trabajadores_crear', False),
                'editar': self.cleaned_data.get('trabajadores_editar', False),
                'eliminar': self.cleaned_data.get('trabajadores_eliminar', False),
            },
            'asistencias': {
                'ver': self.cleaned_data.get('asistencias_ver', False),
                'crear': self.cleaned_data.get('asistencias_crear', False),
                'validar': self.cleaned_data.get('asistencias_validar', False),
                'corregir': self.cleaned_data.get('asistencias_corregir', False),
            },
            'planillas': {
                'ver': self.cleaned_data.get('planillas_ver', False),
                'crear': self.cleaned_data.get('planillas_crear', False),
                'aprobar_gerente': self.cleaned_data.get('planillas_aprobar_gerente', False),
                'aprobar_contador': self.cleaned_data.get('planillas_aprobar_contador', False),
            },
            'contratistas': {
                'ver': self.cleaned_data.get('contratistas_ver', False),
                'crear': self.cleaned_data.get('contratistas_crear', False),
                'editar': self.cleaned_data.get('contratistas_editar', False),
                'eliminar': self.cleaned_data.get('contratistas_eliminar', False),
            },
            'reportes': {
                'ver': self.cleaned_data.get('reportes_ver', False),
                'exportar': self.cleaned_data.get('reportes_exportar', False),
            },
            'admin_panel': {
                'acceso': self.cleaned_data.get('admin_panel_acceso', False),
            }
        }
        
        # Generar código automáticamente si no existe
        if not instance.codigo:
            instance.codigo = slugify(instance.nombre)
        
        if commit:
            instance.save()
        return instance

class AsignarRolForm(forms.ModelForm):
    """Formulario para asignar rol a usuario"""
    
    class Meta:
        model = Usuario
        fields = ['rol', 'cuenta_aprobada']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_aprobada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].queryset = Rol.objects.filter(activo=True)
        self.fields['rol'].required = True