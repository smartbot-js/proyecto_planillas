"""
Serializers para el módulo de trabajadores
Utilizados por el API REST para la aplicación móvil
"""

from rest_framework import serializers
from .models import Trabajador, HistorialProyecto, DocumentoTrabajador
from apps.proyectos.models import Proyecto


class ProyectoSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple para mostrar información básica del proyecto"""
    
    class Meta:
        model = Proyecto
        fields = ['id', 'nombre']


class TrabajadorListSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para listados de trabajadores
    Usado en listas de la app móvil
    """
    proyecto_nombre = serializers.CharField(source='proyecto_asignado.nombre', read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    foto_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Trabajador
        fields = [
            'id',
            'nombre_completo',
            'nombre',
            'apellido',
            'numero_cedula',
            'puesto_laboral',
            'proyecto_nombre',
            'foto_url',
            'estado',
            'asegurado',
        ]
    
    def get_foto_url(self, obj):
        """Retorna la URL completa de la foto si existe"""
        if obj.foto:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto.url)
        return None


class TrabajadorSerializer(serializers.ModelSerializer):
    """
    Serializer completo para trabajadores
    Usado en detalles y creación/actualización desde la app móvil
    """
    proyecto_asignado_info = ProyectoSimpleSerializer(source='proyecto_asignado', read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    edad = serializers.IntegerField(read_only=True)
    tiempo_servicio = serializers.IntegerField(read_only=True)
    foto_url = serializers.SerializerMethodField()
    foto_cedula_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Trabajador
        fields = [
            'id',
            'nombre',
            'apellido',
            'nombre_completo',
            'numero_cedula',
            'fecha_nacimiento',
            'edad',
            'sexo',
            'tipo_sangre',
            'telefono',
            'email',
            'direccion',
            'departamento',
            'municipio',
            'contacto_emergencia',
            'proyecto_asignado',
            'proyecto_asignado_info',
            'puesto_laboral',
            'area_cargo',
            'salario_normal',
            'tarifa_hora_extra',
            'numero_seguro_social',
            'asegurado',
            'record_policia',
            'estado',
            'fecha_ingreso',
            'tiempo_servicio',
            'foto_url',
            'foto_cedula_url',
            'notas',
            'creado_en',
            'modificado_en',
        ]
        read_only_fields = ['id', 'creado_en', 'modificado_en']
    
    def get_foto_url(self, obj):
        """Retorna la URL completa de la foto del trabajador"""
        if obj.foto:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto.url)
        return None
    
    def get_foto_cedula_url(self, obj):
        """Retorna la URL completa de la foto de la cédula"""
        if obj.foto_cedula:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto_cedula.url)
        elif obj.foto_cedula_frontal:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto_cedula_frontal.url)
        return None


class TrabajadorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear trabajadores desde la app móvil
    """
    
    class Meta:
        model = Trabajador
        fields = [
            'nombre',
            'apellido',
            'numero_cedula',
            'fecha_nacimiento',
            'sexo',
            'telefono',
            'email',
            'direccion',
            'departamento',
            'municipio',
            'contacto_emergencia',
            'proyecto_asignado',
            'puesto_laboral',
            'area_cargo',
            'salario_normal',
            'tarifa_hora_extra',
            'numero_seguro_social',
            'asegurado',
            'estado',
            'notas',
        ]
    
    def validate_numero_cedula(self, value):
        """Valida que la cédula sea única"""
        if Trabajador.objects.filter(numero_cedula=value, eliminado=False).exists():
            raise serializers.ValidationError("Ya existe un trabajador con esta cédula.")
        return value
    
    def create(self, validated_data):
        """Crea el trabajador con el usuario actual"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['creado_por'] = request.user
            validated_data['modificado_por'] = request.user
        return super().create(validated_data)


class HistorialProyectoSerializer(serializers.ModelSerializer):
    """Serializer para historial de proyectos del trabajador"""
    
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True)
    dias_trabajados = serializers.SerializerMethodField()
    
    class Meta:
        model = HistorialProyecto
        fields = [
            'id',
            'proyecto',
            'proyecto_nombre',
            'fecha_asignacion',
            'fecha_salida',
            'motivo',
            'dias_trabajados',
            'creado_en',
        ]
    
    def get_dias_trabajados(self, obj):
        """Calcula los días trabajados en el proyecto"""
        if obj.fecha_salida:
            delta = obj.fecha_salida - obj.fecha_asignacion
            return delta.days
        else:
            from django.utils import timezone
            delta = timezone.now().date() - obj.fecha_asignacion
            return delta.days


class DocumentoTrabajadorSerializer(serializers.ModelSerializer):
    """Serializer para documentos adicionales del trabajador"""
    
    archivo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentoTrabajador
        fields = [
            'id',
            'tipo_documento',
            'nombre_documento',
            'archivo_url',
            'fecha_emision',
            'fecha_vencimiento',
            'notas',
            'creado_en',
        ]
    
    def get_archivo_url(self, obj):
        """Retorna la URL completa del archivo"""
        if obj.archivo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.archivo.url)
        return None
    