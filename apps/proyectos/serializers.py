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
    presupuesto_disponible = serializers.SerializerMethodField()
    porcentaje_gastado = serializers.SerializerMethodField()
    dias_transcurridos = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    
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
            'presupuesto',
            'presupuesto_gastado',
            'presupuesto_disponible',
            'porcentaje_gastado',
            'dias_transcurridos',
            'dias_restantes',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_presupuesto_disponible(self, obj):
        return float(obj.presupuesto_disponible())
    
    def get_porcentaje_gastado(self, obj):
        return round(obj.porcentaje_gastado(), 2)
    
    def get_dias_transcurridos(self, obj):
        return obj.dias_transcurridos()
    
    def get_dias_restantes(self, obj):
        return obj.dias_restantes()


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
            'presupuesto',
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
    
    def validate_presupuesto(self, value):
        """Validar que el presupuesto sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("El presupuesto debe ser mayor a 0")
        return value
    
    def validate_supervisor(self, value):
        """Validar que el supervisor tenga el rol adecuado"""
        if not value.puede_validar_asistencias():
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
            'fecha_fin_real',
            'supervisor',
            'estado',
            'presupuesto',
            'presupuesto_gastado',
        ]
    
    def validate_presupuesto_gastado(self, value):
        """Validar que el presupuesto gastado no supere el total"""
        presupuesto = self.instance.presupuesto
        if 'presupuesto' in self.initial_data:
            presupuesto = self.initial_data.get('presupuesto')
        
        if value > presupuesto:
            raise serializers.ValidationError(
                "El presupuesto gastado no puede superar el presupuesto total"
            )
        return value
    
    # def validate_fecha_fin_real(self, value):
    #     """Validar que la fecha fin real sea posterior al inicio"""
    #     if value and value < self.instance.fecha_inicio:
    #         raise serializers.ValidationError(
    #             "La fecha fin real debe ser posterior a la fecha de inicio"
    #         )
    #     return value


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
    porcentaje_gastado = serializers.SerializerMethodField()
    
    class Meta:
        model = Proyecto
        fields = [
            'id',
            'nombre',
            'ubicacion',
            'supervisor_nombre',
            'estado',
            'estado_display',
            'presupuesto',
            'porcentaje_gastado',
            'fecha_inicio',
            'fecha_fin_estimada',
        ]
    
    def get_porcentaje_gastado(self, obj):
        return round(obj.porcentaje_gastado(), 2)


class ProyectoDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer detallado con información completa del supervisor
    """
    supervisor = UsuarioSerializer(read_only=True)
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    presupuesto_disponible = serializers.SerializerMethodField()
    porcentaje_gastado = serializers.SerializerMethodField()
    dias_transcurridos = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    
    class Meta:
        model = Proyecto
        fields = '__all__'
    
    def get_presupuesto_disponible(self, obj):
        return float(obj.presupuesto_disponible())
    
    def get_porcentaje_gastado(self, obj):
        return round(obj.porcentaje_gastado(), 2)
    
    def get_dias_transcurridos(self, obj):
        return obj.dias_transcurridos()
    
    def get_dias_restantes(self, obj):
        return obj.dias_restantes()
    
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
        