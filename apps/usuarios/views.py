"""
Views para la aplicación de usuarios
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import Usuario
from .serializers import (
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    UsuarioPerfilSerializer,
)


# ========================================
# VISTAS API REST (para la app móvil)
# ========================================

class UsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD de usuarios (API)
    """
    queryset = Usuario.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        return UsuarioSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Usuario.objects.all()
        
        if not user.es_administrador():
            queryset = queryset.filter(activo=True)
        
        # Filtros
        rol = self.request.query_params.get('rol', None)
        activo = self.request.query_params.get('activo', None)
        search = self.request.query_params.get('search', None)
        
        if rol:
            queryset = queryset.filter(rol=rol)
        
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(nombre_completo__icontains=search)
            )
        
        return queryset.order_by('-fecha_creacion')
    
    def perform_destroy(self, instance):
        instance.activo = False
        instance.save()
    
    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        usuario.activo = True
        usuario.save()
        serializer = self.get_serializer(usuario)
        return Response({
            'message': 'Usuario activado exitosamente',
            'usuario': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        if usuario.id == request.user.id:
            return Response(
                {'error': 'No puedes desactivar tu propia cuenta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        usuario.activo = False
        usuario.save()
        serializer = self.get_serializer(usuario)
        return Response({
            'message': 'Usuario desactivado exitosamente',
            'usuario': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def supervisores(self, request):
        supervisores = Usuario.objects.filter(
            rol=Usuario.Rol.SUPERVISOR,
            activo=True
        )
        serializer = self.get_serializer(supervisores, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trabajadores(self, request):
        trabajadores = Usuario.objects.filter(
            rol=Usuario.Rol.TRABAJADOR,
            activo=True
        )
        serializer = self.get_serializer(trabajadores, many=True)
        return Response(serializer.data)


class LoginView(APIView):
    """Vista API para autenticación"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            auth_login(request, user)
            user_serializer = UsuarioSerializer(user)
            
            return Response({
                'token': token.key,
                'user': user_serializer.data,
                'message': 'Inicio de sesión exitoso'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Vista API para cerrar sesión"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            request.user.auth_token.delete()
        except:
            pass
        auth_logout(request)
        return Response({'message': 'Sesión cerrada exitosamente'}, status=status.HTTP_200_OK)


class PerfilView(APIView):
    """Vista API para perfil del usuario"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UsuarioPerfilSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UsuarioPerfilSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Perfil actualizado exitosamente',
                'user': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Vista API para cambiar contraseña"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            try:
                request.user.auth_token.delete()
            except:
                pass
            return Response({
                'message': 'Contraseña cambiada exitosamente. Por favor inicie sesión nuevamente.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """Vista API para obtener usuario actual"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)


# ========================================
# VISTAS DE TEMPLATES (para la web)
# ========================================

class LoginTemplateView(View):
    """Vista para mostrar y procesar el formulario de login"""
    template_name = 'usuarios/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')
        
        # Debug: Imprimir lo que llega
        print(f"Intento de login - Email: {email}")
        
        # Verificar que el usuario exista
        try:
            usuario = Usuario.objects.get(email=email)
            print(f"Usuario encontrado: {usuario.email}, Activo: {usuario.activo}")
        except Usuario.DoesNotExist:
            print(f"Usuario NO encontrado con email: {email}")
            messages.error(request, 'No existe un usuario con este correo electrónico.')
            return render(request, self.template_name)
        
        # Autenticar usuario
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            print(f"Autenticación exitosa para: {email}")
            
            if user.activo:
                auth_login(request, user)
                
                if not remember:
                    request.session.set_expiry(0)
                
                messages.success(request, f'¡Bienvenido {user.nombre_completo}!')
                
                # Redirigir según rol
                if user.es_administrador():
                    return redirect('dashboard')
                elif user.es_supervisor():
                    return redirect('dashboard')
                else:
                    return redirect('dashboard')
            else:
                print(f"Usuario {email} está desactivado")
                messages.error(request, 'Tu cuenta está desactivada.')
        else:
            print(f"Autenticación FALLIDA para: {email}")
            messages.error(request, 'Credenciales incorrectas. Verifica tu correo y contraseña.')
        
        return render(request, self.template_name)

class RegistroTemplateView(View):
    """Vista para registro de nuevos usuarios"""
    template_name = 'usuarios/login.html'
    
    def post(self, request):
        email = request.POST.get('email', '').strip()
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        rol = request.POST.get('rol', 'trabajador')
        
        # Validaciones
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, self.template_name)
        
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado.')
            return render(request, self.template_name)
        
        try:
            # IMPORTANTE: Usar create_user() NO create()
            usuario = Usuario.objects.create_user(  # ← Esto es clave
                email=email,
                nombre_completo=nombre_completo,
                password=password,  # Se encripta automáticamente
                rol=rol,
                activo=True
            )
            
            messages.success(request, '¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.')
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return render(request, self.template_name)

class LogoutTemplateView(View):
    """Vista para cerrar sesión"""
    def get(self, request):
        auth_logout(request)
        messages.success(request, 'Sesión cerrada exitosamente.')
        return redirect('login')


@method_decorator(login_required(login_url='login'), name='dispatch')
class DashboardView(View):
    """Vista del dashboard principal"""
    template_name = 'usuarios/dashboard.html'
    
    def get(self, request):
        context = {
            'usuario': request.user,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required(login_url='login'), name='dispatch')
class PerfilTemplateView(View):
    """Vista del perfil del usuario"""
    template_name = 'usuarios/perfil.html'
    
    def get(self, request):
        context = {
            'usuario': request.user,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        user = request.user
        user.nombre_completo = request.POST.get('nombre_completo', user.nombre_completo)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        messages.success(request, 'Perfil actualizado exitosamente.')
        return redirect('perfil')
    