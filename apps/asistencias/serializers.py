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
    
    # Campos de validación (agregar a la clase AsistenciaSerializer)
    validado_por_nombre = serializers.CharField(
        source='validado_por.nombre_completo',
        read_only=True,
        allow_null=True
    )
    corregida_por_nombre = serializers.CharField(
        source='corregida_por.nombre_completo',
        read_only=True,
        allow_null=True
    )
    puede_ser_validada = serializers.BooleanField(read_only=True)
    necesita_validacion = serializers.BooleanField(read_only=True)

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
            'horas_nocturnas',
            'horas_festivas',
            'puesto_laboral',
            'salario_dia',
            'tarifa_hora_extra',
            'salario_hora_festiva',
            'salario_hora_nocturna',
            'es_dia_festivo',
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
            'validado',
            'validado_por',
            'validado_por_nombre',
            'validado_fecha',
            'observaciones_validacion',
            'fue_corregida',
            'corregida_por',
            'corregida_por_nombre',
            'corregida_fecha',
            'motivo_correccion',
            'hora_entrada_original',
            'hora_salida_original',
            'puede_ser_validada',
            'necesita_validacion',
        ]
        read_only_fields = [
            'horas_normales',
            'horas_extras',
            'horas_totales',
            'horas_nocturnas',
            'horas_festivas',
            'salario_dia',
            'tarifa_hora_extra',
            'salario_hora_festiva',
            'salario_hora_nocturna',
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
            'horas_nocturnas',
            'horas_festivas',
            'duracion_jornada',
            'es_dia_festivo',
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
    
    trabajador_cedula = serializers.CharField(max_length=50, required=True)
    proyecto_id = serializers.IntegerField(required=True)
    hora_entrada = serializers.TimeField(required=False, allow_null=True)
    fecha_app = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    latitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    metodo_identificacion = serializers.ChoiceField(
        choices=Asistencia.METODO_CHOICES,
        default='qr'
    )
    dispositivo_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class CheckOutSerializer(serializers.Serializer):
    """Serializer para marcar salida (check-out)"""
    
    asistencia_id = serializers.IntegerField(required=True)
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    fecha_app = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    latitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

class SincronizarAsistenciaItemSerializer(serializers.Serializer):
    """
    Serializer para sincronización batch
    - tipo "entrada": requiere trabajador_cedula, proyecto_id, fecha, hora_entrada
    - tipo "salida": requiere asistencia_temp_id, hora_salida
    """
    # Identificador temporal (requerido para salida, opcional para entrada)
    asistencia_temp_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Tipo de registro
    tipo = serializers.ChoiceField(choices=['entrada', 'salida'], required=True)
    
    # Campos para ENTRADA
    trabajador_cedula = serializers.CharField(max_length=50, required=False, allow_blank=True)
    proyecto_id = serializers.IntegerField(required=False, allow_null=True)
    fecha = serializers.DateField(format="%Y-%m-%d", required=False, allow_null=True)
    hora_entrada = serializers.TimeField(required=False, allow_null=True)
    latitud_entrada = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud_entrada = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    
    # Campos para SALIDA
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    latitud_salida = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitud_salida = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    
    # Campos opcionales
    metodo_identificacion = serializers.ChoiceField(
        choices=[('qr', 'QR'), ('nfc', 'NFC'), ('facial', 'Facial'), ('huella', 'Huella'), ('manual', 'Manual')],
        default='qr',
        required=False
    )
    dispositivo_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        tipo = data.get('tipo')
        
        if tipo == 'entrada':
            if not data.get('trabajador_cedula'):
                raise serializers.ValidationError({'trabajador_cedula': 'Requerido para entrada.'})
            if not data.get('proyecto_id'):
                raise serializers.ValidationError({'proyecto_id': 'Requerido para entrada.'})
            if not data.get('fecha'):
                raise serializers.ValidationError({'fecha': 'Requerido para entrada.'})
            if not data.get('hora_entrada'):
                raise serializers.ValidationError({'hora_entrada': 'Requerido para entrada.'})
        
        elif tipo == 'salida':
            if not data.get('asistencia_temp_id') and data.get('asistencia_temp_id') != 0:
                raise serializers.ValidationError({'asistencia_temp_id': 'Requerido para salida.'})
            if not data.get('hora_salida'):
                raise serializers.ValidationError({'hora_salida': 'Requerido para salida.'})
        
        return data


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
        
class ValidarAsistenciaSerializer(serializers.Serializer):
    """
    Serializer para validar una asistencia
    
    Campos:
        observaciones: Observaciones opcionales del supervisor
    """
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text='Observaciones opcionales al validar'
    )
    
    def validate(self, data):
        """
        Validaciones adicionales
        """
        # Obtener la asistencia del contexto
        asistencia = self.context.get('asistencia')
        
        if not asistencia:
            raise serializers.ValidationError('Asistencia no encontrada en el contexto')
        
        if asistencia.validado:
            raise serializers.ValidationError('Esta asistencia ya fue validada')
        
        if asistencia.estado != 'cerrado':
            raise serializers.ValidationError('Solo se pueden validar asistencias cerradas')
        
        if asistencia.eliminado:
            raise serializers.ValidationError('No se puede validar una asistencia eliminada')
        
        return data


class RechazarAsistenciaSerializer(serializers.Serializer):
    """
    Serializer para rechazar una asistencia
    
    Campos:
        motivo: Motivo del rechazo (obligatorio)
    """
    motivo = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=1000,
        help_text='Motivo por el cual se rechaza la asistencia'
    )
    
    def validate_motivo(self, value):
        """
        Valida que el motivo no esté vacío
        """
        if not value or value.strip() == '':
            raise serializers.ValidationError('El motivo del rechazo es obligatorio')
        
        if len(value.strip()) < 10:
            raise serializers.ValidationError('El motivo debe tener al menos 10 caracteres')
        
        return value.strip()
    
    def validate(self, data):
        """
        Validaciones adicionales
        """
        asistencia = self.context.get('asistencia')
        
        if not asistencia:
            raise serializers.ValidationError('Asistencia no encontrada en el contexto')
        
        if asistencia.validado:
            raise serializers.ValidationError('No se puede rechazar una asistencia ya validada')
        
        if asistencia.eliminado:
            raise serializers.ValidationError('No se puede rechazar una asistencia eliminada')
        
        return data


class CorregirAsistenciaSerializer(serializers.Serializer):
    """
    Serializer para corregir marcaciones de una asistencia
    
    Campos:
        nueva_hora_entrada: Nueva hora de entrada (opcional)
        nueva_hora_salida: Nueva hora de salida (opcional)
        motivo_correccion: Motivo de la corrección (obligatorio)
    """
    nueva_hora_entrada = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text='Nueva hora de entrada (formato HH:MM:SS)'
    )
    nueva_hora_salida = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text='Nueva hora de salida (formato HH:MM:SS)'
    )
    motivo_correccion = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=1000,
        help_text='Motivo de la corrección (obligatorio)'
    )
    
    def validate_motivo_correccion(self, value):
        """
        Valida que el motivo no esté vacío
        """
        if not value or value.strip() == '':
            raise serializers.ValidationError('El motivo de la corrección es obligatorio')
        
        if len(value.strip()) < 10:
            raise serializers.ValidationError('El motivo debe tener al menos 10 caracteres')
        
        return value.strip()
    
    def validate(self, data):
        """
        Validaciones adicionales
        """
        asistencia = self.context.get('asistencia')
        
        if not asistencia:
            raise serializers.ValidationError('Asistencia no encontrada en el contexto')
        
        # Al menos una hora debe ser proporcionada
        if not data.get('nueva_hora_entrada') and not data.get('nueva_hora_salida'):
            raise serializers.ValidationError(
                'Debe especificar al menos una hora para corregir (entrada o salida)'
            )
        
        # Validar lógica de horas
        nueva_entrada = data.get('nueva_hora_entrada')
        nueva_salida = data.get('nueva_hora_salida')
        
        # Si se proporcionan ambas, validar que salida sea después de entrada
        if nueva_entrada and nueva_salida:
            if nueva_salida <= nueva_entrada:
                raise serializers.ValidationError(
                    'La hora de salida debe ser posterior a la hora de entrada'
                )
        
        # Si solo se proporciona salida, validar contra entrada actual
        if nueva_salida and not nueva_entrada:
            if asistencia.hora_entrada and nueva_salida <= asistencia.hora_entrada:
                raise serializers.ValidationError(
                    'La hora de salida debe ser posterior a la hora de entrada actual'
                )
        
        if asistencia.eliminado:
            raise serializers.ValidationError('No se puede corregir una asistencia eliminada')
        
        return data
    
# ========================================
# SERIALIZER PARA LISTA DE PENDIENTES
# ========================================

class AsistenciaPendienteValidacionSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para lista de asistencias pendientes de validación
    """
    trabajador_nombre = serializers.CharField(
        source='trabajador.nombre_completo',
        read_only=True
    )
    proyecto_nombre = serializers.CharField(
        source='proyecto.nombre',
        read_only=True
    )
    duracion_jornada = serializers.CharField(read_only=True)
    
    class Meta:
        model = Asistencia
        fields = [
            'id',
            'fecha',
            'trabajador',
            'trabajador_nombre',
            'proyecto',
            'proyecto_nombre',
            'hora_entrada',
            'hora_salida',
            'horas_totales',
            'horas_extras',
            'estado',
            'llego_tarde',
            'minutos_tarde',
            'duracion_jornada',
            'observaciones',
        ]
        read_only_fields = fields

