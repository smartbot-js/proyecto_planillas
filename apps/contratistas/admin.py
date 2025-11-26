"""
Configuración del Admin para Contratistas
apps/contratistas/admin.py
"""
from django.contrib import admin
from .models import Contratista, ContratoProyecto, PagoContratista


@admin.register(Contratista)
class ContratistaAdmin(admin.ModelAdmin):
    list_display = ['numero_cedula', 'nombre_completo', 'telefono', 'activo', 'total_contratos']
    list_filter = ['activo', 'departamento']
    search_fields = ['nombre', 'apellido', 'numero_cedula', 'telefono']
    readonly_fields = ['creado_en', 'modificado_en']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'apellido', 'numero_cedula', 'foto_cedula')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email', 'direccion', 'departamento', 'municipio')
        }),
        ('Datos Bancarios', {
            'fields': ('banco', 'numero_cuenta', 'tipo_cuenta', 'moneda_cuenta')
        }),
        ('Estado', {
            'fields': ('activo', 'eliminado')
        }),
        ('Metadata', {
            'fields': ('creado_por', 'creado_en', 'modificado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContratoProyecto)
class ContratoProyectoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'contratista', 'proyecto', 'valor_contrato', 'estado', 'porcentaje_avance']
    list_filter = ['estado', 'proyecto']
    search_fields = ['codigo', 'contratista__nombre', 'contratista__apellido', 'proyecto__nombre']
    readonly_fields = ['codigo', 'creado_en', 'modificado_en', 'total_pagado', 'total_pendiente', 'porcentaje_avance']
    
    fieldsets = (
        ('Información del Contrato', {
            'fields': ('codigo', 'contratista', 'proyecto', 'descripcion', 'actividades')
        }),
        ('Valores y Fechas', {
            'fields': ('valor_contrato', 'fecha_inicio', 'fecha_fin', 'estado')
        }),
        ('Avance', {
            'fields': ('total_pagado', 'total_pendiente', 'porcentaje_avance'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('eliminado', 'creado_por', 'creado_en', 'modificado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PagoContratista)
class PagoContratistaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'contrato', 'fecha_pago', 'monto_cordobas', 'forma_pago', 'estado']
    list_filter = ['estado', 'forma_pago', 'fecha_pago']
    search_fields = ['codigo', 'contrato__codigo', 'contrato__contratista__nombre', 'concepto']
    readonly_fields = ['codigo', 'monto_dolares', 'creado_en', 'modificado_en', 'fecha_ingreso']
    
    fieldsets = (
        ('Información del Pago', {
            'fields': ('codigo', 'contrato', 'fecha_pago', 'concepto')
        }),
        ('Montos', {
            'fields': ('monto_cordobas', 'monto_dolares', 'tipo_cambio', 'forma_pago')
        }),
        ('Soporte', {
            'fields': ('archivo_soporte',)
        }),
        ('Aprobaciones', {
            'fields': (
                'estado',
                'ingresado_por', 'fecha_ingreso',
                'aprobado_gerente_por', 'fecha_aprobacion_gerente',
                'aprobado_contador_por', 'fecha_aprobacion_contador',
                'motivo_rechazo'
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('eliminado', 'creado_en', 'modificado_en'),
            'classes': ('collapse',)
        }),
    )