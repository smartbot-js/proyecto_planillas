"""
Serializers para la aplicación de usuarios
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y ver detalles de usuarios
    """
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'email',
            'nombre_completo',
            'rol',
            'rol_display',
            'activo',
            'is_staff',
            'fecha_creacion',
            'fecha_actualizacion',
            'last_login',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'last_login']


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear nuevos usuarios
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = Usuario
        fields = [
            'email',
            'nombre_completo',
            'rol',
            'password',
            'password_confirm',
            'activo',
        ]
    
    def validate(self, attrs):
        """
        Validar que las contraseñas coincidan
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Las contraseñas no coinciden"
            })
        return attrs
    
    def create(self, validated_data):
        """
        Crear usuario con contraseña encriptada
        """
        # Remover password_confirm ya que no es parte del modelo
        validated_data.pop('password_confirm')
        
        # Crear usuario usando el manager personalizado
        user = Usuario.objects.create_user(**validated_data)
        return user


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar usuarios existentes
    """
    class Meta:
        model = Usuario
        fields = [
            'email',
            'nombre_completo',
            'rol',
            'activo',
        ]
    
    def validate_email(self, value):
        """
        Validar que el email no esté en uso por otro usuario
        """
        user = self.instance
        if Usuario.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está en uso por otro usuario")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambiar contraseña
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """
        Validar que la contraseña actual sea correcta
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta")
        return value
    
    def validate(self, attrs):
        """
        Validar que las contraseñas nuevas coincidan
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "Las contraseñas no coinciden"
            })
        return attrs
    
    def save(self, **kwargs):
        """
        Cambiar la contraseña del usuario
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer para autenticación de usuarios
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """
        Validar credenciales del usuario
        """
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Autenticar usuario
            user = authenticate(
                request=self.context.get('request'),
                username=email,  # Usamos email como username
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    "No se pudo iniciar sesión con las credenciales proporcionadas",
                    code='authorization'
                )
            
            if not user.activo:
                raise serializers.ValidationError(
                    "Esta cuenta está desactivada",
                    code='authorization'
                )
            
        else:
            raise serializers.ValidationError(
                "Debe incluir 'email' y 'password'",
                code='authorization'
            )
        
        attrs['user'] = user
        return attrs


class UsuarioPerfilSerializer(serializers.ModelSerializer):
    """
    Serializer para ver y actualizar el perfil del usuario actual
    """
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'email',
            'nombre_completo',
            'rol',
            'rol_display',
            'fecha_creacion',
            'last_login',
        ]
        read_only_fields = ['id', 'rol', 'fecha_creacion', 'last_login']
        