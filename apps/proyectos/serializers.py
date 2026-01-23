"""
Serializers para la aplicación de proyectos
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Proyecto
from apps.usuarios.serializers import UsuarioSerializer


class ProyectoSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y ver detalles de proyectos
    """
    supervisor_nombre = serializers.CharField(
        source='supervisor.nombre_completo',
        read_only=True
    )
    supervisor_email = serializers.CharField(
        source='supervisor.email',
        read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    # Usar las properties del modelo
    presupuesto_disponible = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    porcentaje_gastado = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Proyecto
        fields = [
            'id',
            'nombre',
            'descripcion',
            'ubicacion',
            'fecha_inicio',
            'fecha_fin_estimada',
            'supervisor',
            'supervisor_nombre',
            'supervisor_email',
            'estado',
            'estado_display',
            'presupuesto_total',
            'presupuesto_mano_obra',
            'presupuesto_administrativo',
            'gasto_mano_obra_real',
            'gasto_administrativo_real',
            'presupuesto_disponible',
            'porcentaje_gastado',
            'porcentaje_avance_general',
            'activo',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']


class ProyectoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear proyectos
    """
    class Meta:
        model = Proyecto
        fields = [
            'nombre',
            'descripcion',
            'ubicacion',
            'fecha_inicio',
            'fecha_fin_estimada',
            'supervisor',
            'presupuesto_total',
            'presupuesto_mano_obra',
            'presupuesto_administrativo',
            'estado',
        ]
    
    def validate_fecha_inicio(self, value):
        """Validar que la fecha de inicio no sea muy antigua"""
        from datetime import timedelta
        if value < (timezone.now().date() - timedelta(days=365)):
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser mayor a 1 año en el pasado"
            )
        return value
    
    def validate_fecha_fin_estimada(self, value):
        """Validar que la fecha fin estimada sea posterior al inicio"""
        if value and 'fecha_inicio' in self.initial_data:
            fecha_inicio = self.initial_data.get('fecha_inicio')
            if value < fecha_inicio:
                raise serializers.ValidationError(
                    "La fecha fin estimada debe ser posterior a la fecha de inicio"
                )
        return value
    
    def validate_presupuesto_total(self, value):
        """Validar que el presupuesto sea mayor o igual a 0"""
        if value is not None and value < 0:
            raise serializers.ValidationError("El presupuesto no puede ser negativo")
        return value
    
    def validate_supervisor(self, value):
        """Validar que el supervisor tenga el rol adecuado"""
        if hasattr(value, 'puede_validar_asistencias') and not value.puede_validar_asistencias():
            raise serializers.ValidationError(
                "El usuario seleccionado no tiene permisos de supervisor"
            )
        return value


class ProyectoUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar proyectos
    """
    class Meta:
        model = Proyecto
        fields = [
            'nombre',
            'descripcion',
            'ubicacion',
            'fecha_inicio',
            'fecha_fin_estimada',
            'supervisor',
            'estado',
            'presupuesto_total',
            'presupuesto_mano_obra',
            'presupuesto_administrativo',
            'gasto_mano_obra_real',
            'gasto_administrativo_real',
        ]


class ProyectoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar proyectos (más ligero)
    """
    supervisor_nombre = serializers.CharField(
        source='supervisor.nombre_completo',
        read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    porcentaje_gastado = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Proyecto
        fields = [
            'id',
            'nombre',
            'ubicacion',
            'supervisor_nombre',
            'estado',
            'estado_display',
            'presupuesto_total',
            'porcentaje_gastado',
            'porcentaje_avance_general',
            'fecha_inicio',
            'fecha_fin_estimada',
            'activo',
        ]


class ProyectoDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer detallado con información completa del supervisor
    """
    supervisor = UsuarioSerializer(read_only=True)
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    presupuesto_disponible = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    porcentaje_gastado = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Proyecto
        fields = '__all__'

    
class MisProyectosSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para el endpoint mis-proyectos
    Solo retorna los campos esenciales para la app móvil
    """
    supervisor_nombre = serializers.CharField(
        source='supervisor.nombre_completo',
        read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    trabajadores_count = serializers.SerializerMethodField()
    asistencias_hoy = serializers.SerializerMethodField()
    
    class Meta:
        model = Proyecto
        fields = [
            'id',
            'nombre',
            'descripcion',
            'ubicacion',
            'ubicacion_coordenadas',
            'latitud',
            'longitud',
            'radio_geovalla',
            'estado',
            'estado_display',
            'supervisor',
            'supervisor_nombre',
            'fecha_inicio',
            'fecha_fin_estimada',
            'porcentaje_avance_general',
            'trabajadores_count',
            'asistencias_hoy',
            # Horarios por día
            'hora_inicio_lunes',
            'hora_fin_lunes',
            'hora_inicio_martes',
            'hora_fin_martes',
            'hora_inicio_miercoles',
            'hora_fin_miercoles',
            'hora_inicio_jueves',
            'hora_fin_jueves',
            'hora_inicio_viernes',
            'hora_fin_viernes',
            'hora_inicio_sabado',
            'hora_fin_sabado',
            'hora_inicio_domingo',
            'hora_fin_domingo',
            'minutos_tolerancia_entrada',
            'minutos_tolerancia_salida',
            'dias_laborales',
        ]
    
    def get_trabajadores_count(self, obj):
        """Cantidad de trabajadores asignados"""
        return obj.trabajadores.filter(eliminado=False, estado='activo').count()
    
    def get_asistencias_hoy(self, obj):
        """Cantidad de asistencias registradas hoy"""
        from django.utils import timezone
        from apps.asistencias.models import Asistencia
        
        return Asistencia.objects.filter(
            proyecto=obj,
            fecha=timezone.now().date(),
            eliminado=False
        ).count()
        