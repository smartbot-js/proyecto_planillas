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
from django.views.decorators.csrf import csrf_exempt
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
            rol__codigo__in=['gerente_proyecto', 'gerente_general'],
            activo=True
        )
        serializer = self.get_serializer(supervisores, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trabajadores(self, request):
        trabajadores = Usuario.objects.filter(
            rol__codigo='asistencia',
            activo=True
        )
        serializer = self.get_serializer(trabajadores, many=True)
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
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

@method_decorator(csrf_exempt, name='dispatch')
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
        #return render(request, self.template_name)
        context = {
        'roles': Usuario.Rol.choices
            }
        return render(request, self.template_name, context)
    
    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')
        context = {
            'roles': Usuario.Rol.choices
        }
        # Debug: Imprimir lo que llega
        print(f"Intento de login - Email: {email}")
        
        # Verificar que el usuario exista
        try:
            usuario = Usuario.objects.get(email=email)
            print(f"Usuario encontrado: {usuario.email}, Activo: {usuario.activo}")
        except Usuario.DoesNotExist:
            print(f"Usuario NO encontrado con email: {email}")
            messages.error(request, 'No existe un usuario con este correo electrónico.')
            #return render(request, self.template_name)
            return render(request, self.template_name, context)
        
        # Autenticar usuario
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            print(f"Autenticación exitosa para: {email}")
            
            # ========== AGREGAR VALIDACIÓN DE APROBACIÓN ==========
            if not user.cuenta_aprobada and not user.is_superuser:
                messages.warning(
                    request,
                    'Tu cuenta está pendiente de aprobación por un administrador. '
                    'Serás notificado cuando tu cuenta sea activada.'
                )
                return render(request, self.template_name, context)
            # ======================================================
            
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
        
        return render(request, self.template_name, context)

class RegistroTemplateView(View):
    """Vista para registro de nuevos usuarios"""
    template_name = 'usuarios/login.html'
    
    def post(self, request):
        email = request.POST.get('email', '').strip()
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        rol_codigo = request.POST.get('rol', '')  # ← Cambiar nombre variable
        
        context = {
            'roles': Usuario.Rol.choices
        }
        
        # Validaciones
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, self.template_name, context)
        
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado.')
            return render(request, self.template_name, context)
        
        try:
            # ========== OBTENER ROL OBJETO ==========
            from apps.admin_panel.models import Rol
            
            # Buscar rol por código (si viene del formulario)
            rol_obj = None
            if rol_codigo:
                try:
                    rol_obj = Rol.objects.get(codigo=rol_codigo, activo=True)
                except Rol.DoesNotExist:
                    # Si no existe, dejarlo sin rol (admin lo asignará)
                    rol_obj = None
            # ========================================
            
            usuario = Usuario.objects.create_user(
                email=email,
                nombre_completo=nombre_completo,
                password=password,
                rol=rol_obj,  # ← Asignar objeto Rol, no string
                activo=True,
                cuenta_aprobada=False,
            )
            
            messages.success(
                request, 
                'Cuenta creada exitosamente. Un administrador revisará tu solicitud '
                'y serás notificado cuando sea aprobada.'
            )
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return render(request, self.template_name, context)
        
class LogoutTemplateView(View):
    """Vista para cerrar sesión"""
    def get(self, request):
        auth_logout(request)
        messages.success(request, 'Sesión cerrada exitosamente.')
        return redirect('login')

@method_decorator(login_required(login_url='login'), name='dispatch')
class DashboardView(View):
    """Vista del dashboard principal con estadísticas reales"""
    template_name = 'usuarios/dashboard.html'
    
    def get(self, request):
        from django.db.models import Sum, Count, Q
        from decimal import Decimal
        from datetime import date, datetime
        from apps.trabajadores.models import Trabajador
        from apps.proyectos.models import Proyecto
        from apps.planillas.models import Planilla
        from apps.asistencias.models import Asistencia
        from apps.contratistas.models import Contratista, ContratoProyecto, DetallePlanillaContratista
        
        # ==========================================
        # ESTADÍSTICAS DE TRABAJADORES
        # ==========================================
        total_trabajadores = Trabajador.objects.filter(eliminado=False).count()
        trabajadores_activos = Trabajador.objects.filter(
            eliminado=False,
            estado='activo'
        ).count()
        trabajadores_asegurados = Trabajador.objects.filter(
            eliminado=False,
            asegurado=True
        ).count()
        
        # ==========================================
        # ESTADÍSTICAS DE PROYECTOS
        # ==========================================
        total_proyectos = Proyecto.objects.filter(eliminado=False).count()
        proyectos_activos = Proyecto.objects.filter(
            eliminado=False,
            estado='ejecucion'
        ).count()
        proyectos_pausados = Proyecto.objects.filter(
            eliminado=False,
            estado='pausado'
        ).count()
        proyectos_finalizados = Proyecto.objects.filter(
            eliminado=False,
            estado='finalizado'
        ).count()
        
        # ==========================================
        # ESTADÍSTICAS DE ASISTENCIAS HOY
        # ==========================================
        hoy = date.today()
        asistencias_hoy = Asistencia.objects.filter(
            fecha=hoy
        ).count()
        
        trabajadores_presentes_hoy = Asistencia.objects.filter(
            fecha=hoy,
            hora_entrada__isnull=False
        ).values('trabajador').distinct().count()
        
        # ==========================================
        # ESTADÍSTICAS DE PLANILLAS
        # ==========================================
        planillas_pendientes = Planilla.objects.filter(
            eliminado=False,
            estado__in=['borrador', 'aprobada_gerente']
        ).count()
        
        planillas_pagadas_mes = Planilla.objects.filter(
            eliminado=False,
            estado='pagada',
            fecha_generacion__month=hoy.month,
            fecha_generacion__year=hoy.year
        ).count()
        
        total_pagado_mes = Planilla.objects.filter(
            eliminado=False,
            estado='pagada',
            fecha_generacion__month=hoy.month,
            fecha_generacion__year=hoy.year
        ).aggregate(
            total=Sum('total_cordobas')
        )['total'] or Decimal('0.00')
        
        # ==========================================
        # ESTADÍSTICAS DE CONTRATISTAS
        # ==========================================
        total_contratistas = Contratista.objects.filter(
            eliminado=False,
            activo=True
        ).count()
        
        total_contratos = ContratoProyecto.objects.filter(
            eliminado=False
        ).count()
        
        # Total pagado a contratistas (desde planillas pagadas)
        total_pagado_contratistas = DetallePlanillaContratista.objects.filter(
            planilla__estado='pagada'
        ).aggregate(
            total=Sum('monto_cordobas')
        )['total'] or Decimal('0.00')
        
        # ==========================================
        # PROYECTOS RECIENTES (Últimos 5)
        # ==========================================
        proyectos_recientes = Proyecto.objects.filter(
            eliminado=False
        ).select_related('supervisor').order_by('-fecha_creacion')[:5]
        
        # ==========================================
        # PLANILLAS PENDIENTES (Últimas 5)
        # ==========================================
        planillas_pendientes_lista = Planilla.objects.filter(
            eliminado=False,
            estado__in=['borrador', 'aprobada_gerente']
        ).select_related('proyecto').order_by('-fecha_generacion')[:5]
        
        # ==========================================
        # CONTEXTO
        # ==========================================
        context = {
            'usuario': request.user,
            
            # Trabajadores
            'total_trabajadores': total_trabajadores,
            'trabajadores_activos': trabajadores_activos,
            'trabajadores_asegurados': trabajadores_asegurados,
            
            # Proyectos
            'total_proyectos': total_proyectos,
            'proyectos_activos': proyectos_activos,
            'proyectos_pausados': proyectos_pausados,
            'proyectos_finalizados': proyectos_finalizados,
            
            # Asistencias
            'asistencias_hoy': asistencias_hoy,
            'trabajadores_presentes_hoy': trabajadores_presentes_hoy,
            
            # Planillas
            'planillas_pendientes': planillas_pendientes,
            'planillas_pagadas_mes': planillas_pagadas_mes,
            'total_pagado_mes': total_pagado_mes,
            
            # Contratistas
            'total_contratistas': total_contratistas,
            'total_contratos': total_contratos,
            'total_pagado_contratistas': total_pagado_contratistas,
            
            # Listas
            'proyectos_recientes': proyectos_recientes,
            'planillas_pendientes_lista': planillas_pendientes_lista,
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
    