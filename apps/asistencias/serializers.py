"""
Serializers para el módulo de asistencias
API REST para app móvil y web
"""

from rest_framework import serializers
from .models import Asistencia, ResumenDiario
from apps.trabajadores.serializers import TrabajadorListSerializer
from apps.proyectos.serializers import ProyectoSerializer
from django.utils import timezone


class AsistenciaSerializer(serializers.ModelSerializer):
    """Serializer completo para asistencias"""
    
    trabajador_info = TrabajadorListSerializer(source='trabajador', read_only=True)
    proyecto_info = ProyectoSerializer(source='proyecto', read_only=True)
    duracion_jornada = serializers.CharField(read_only=True)
    puede_editar = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Asistencia
        fields = [
            'id',
            'trabajador',
            'trabajador_info',
            'proyecto',
            'proyecto_info',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'horas_normales',
            'horas_extras',
            'horas_totales',
            'puesto_laboral',
            # 'salario_dia',  <-- ELIMINADO
            # 'tarifa_hora_extra', <-- ELIMINADO
            'latitud_entrada',
            'longitud_entrada',
            'distancia_entrada',
            'ubicacion_entrada_valida',
            'latitud_salida',
            'longitud_salida',
            'distancia_salida',
            'ubicacion_salida_valida',
            'estado',
            'llego_tarde',
            'salio_temprano',
            'dispositivo_id',
            'metodo_identificacion',
            'observaciones',
            'duracion_jornada',
            'puede_editar',
            'creado_en',
            'modificado_en',
            'sincronizado_en',
        ]
        read_only_fields = [
            'horas_normales',
            'horas_extras',
            'horas_totales',
            'estado',
            'llego_tarde',
            'salio_temprano',
            'distancia_entrada',
            'ubicacion_entrada_valida',
            'distancia_salida',
            'ubicacion_salida_valida',
            'creado_en',
            'modificado_en',
        ]


class AsistenciaListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    
    trabajador_nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    trabajador_cedula = serializers.CharField(source='trabajador.numero_cedula', read_only=True)
    trabajador_foto = serializers.SerializerMethodField()
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True)
    duracion_jornada = serializers.CharField(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Asistencia
        fields = [
            'id',
            'trabajador_nombre',
            'trabajador_cedula',
            'trabajador_foto',
            'proyecto_nombre',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'horas_normales',
            'horas_extras',
            'horas_totales',
            'duracion_jornada',
            'puesto_laboral',
            'estado',
            'estado_display',
            'llego_tarde',
            'salio_temprano',
            'ubicacion_entrada_valida',
            'puede_editar',
        ]
    
    def get_trabajador_foto(self, obj):
        if obj.trabajador.foto:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.trabajador.foto.url)
        return None


class CheckInSerializer(serializers.Serializer):
    """Serializer para marcar entrada (check-in)"""
    
    trabajador_cedula = serializers.CharField(max_length=50, required=True) # Aumentado a 50 por si acaso
    proyecto_id = serializers.IntegerField(required=True)
    hora_entrada = serializers.TimeField(required=False, allow_null=True)
    latitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    metodo_identificacion = serializers.ChoiceField(
        choices=Asistencia.METODO_CHOICES, # Usar choices del modelo
        default='qr'
    )
    dispositivo_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class CheckOutSerializer(serializers.Serializer):
    """Serializer para marcar salida (check-out)"""
    
    asistencia_id = serializers.IntegerField(required=True)
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    latitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class SincronizarAsistenciaItemSerializer(serializers.Serializer):
    """Serializer para un item de asistencia en el batch"""
    trabajador_cedula = serializers.CharField(max_length=50, required=True)
    proyecto_id = serializers.IntegerField(required=True)
    fecha = serializers.DateField(format="%Y-%m-%d")
    hora_entrada = serializers.TimeField()
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    latitud_entrada = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud_entrada = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    latitud_salida = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud_salida = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    metodo_identificacion = serializers.ChoiceField(
        choices=Asistencia.METODO_CHOICES,
        default='qr'
    )
    dispositivo_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

class SincronizarAsistenciasSerializer(serializers.Serializer):
    """Serializer para sincronización batch desde app móvil"""
    
    asistencias = serializers.ListField(
        child=SincronizarAsistenciaItemSerializer(),
        allow_empty=False
    )


class ResumenDiarioSerializer(serializers.ModelSerializer):
    """Serializer para resúmenes diarios"""
    
    trabajador_nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True)
    
    class Meta:
        model = ResumenDiario
        fields = [
            'id',
            'trabajador',
            'trabajador_nombre',
            'proyecto',
            'proyecto_nombre',
            'fecha',
            'asistio',
            'llego_tarde',
            'horas_totales',
            'horas_extras',
            'observaciones',
        ]
        