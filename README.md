# 🏗️ Sistema de Control de Asistencia y Planillas

Sistema integral para la gestión automatizada de asistencia, generación de planillas y control de pagos para empresas de construcción con múltiples proyectos simultáneos.

## 📋 Tabla de Contenidos

- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Modelo de Datos](#-modelo-de-datos)
- [API Endpoints](#-api-endpoints)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

---

## 🎯 Descripción del Proyecto

### Contexto

La empresa gestiona múltiples proyectos de construcción simultáneos con una plantilla operativa de aproximadamente **400 trabajadores** (albañiles, supervisores, maestros de obra, etc.) distribuidos en campo. Actualmente no existe un sistema automatizado para el registro de asistencia ni la elaboración de planillas, lo cual impacta negativamente en la eficiencia operativa y el control de pagos.

### Objetivo

Diseñar e implementar un sistema compuesto por:
- **Aplicación Web**: Panel administrativo y de gestión
- **Aplicación Móvil**: Control de asistencia en campo con funcionalidad offline

El sistema permite el control automatizado de asistencia por proyecto, generación dinámica de planillas y seguimiento histórico de pagos, considerando validaciones internas y condiciones reales de operación en campo.

---

## ✨ Características Principales

### 1. Gestión de Trabajadores
- Registro único por trabajador con datos completos
- Identificación mediante código de barras de cédula
- Tarifas diferenciadas por cargo (hora/día base)
- Períodos de pago configurables (semanal, quincenal, mensual)
- Posibilidad de traslado entre proyectos

### 2. Gestión de Proyectos
- Registro y gestión de múltiples proyectos simultáneos
- Geolocalización del sitio para validaciones
- Control de fechas (inicio/finalización)
- Seguimiento de porcentaje de avance
- Comparación de avance vs. gastos de planilla
- Asignación dinámica de trabajadores

### 3. Registro de Asistencia
- Marcación diaria de entrada y salida
- Escaneo de código de barras de cédula
- Cálculo automático de horas trabajadas
- Detección de horas extras
- Registro de traslados entre proyectos
- Funcionalidad offline con sincronización posterior

### 4. Validación por Supervisor
- Aprobación o rechazo de registros diarios
- Revisión y corrección de marcaciones erróneas
- Validación de check-in/check-out
- Historial de validaciones realizadas

### 5. Generación de Planillas
- Planillas automáticas por proyecto y trabajador
- Cálculo de horas trabajadas y extras
- Aplicación de tarifas diferenciadas por rol
- Incorporación de bonos (combustible, productividad)
- Desglose de denominaciones bancarias
- Exportación en Excel, PDF e impresión

### 6. Gestión de Contratistas
- Registro de contratistas y contratos
- Definición de actividades y unidades de medida
- Control de fechas y condiciones contractuales
- Seguimiento de nivel de avance
- Carga de archivos soporte de pago
- Sistema de aprobación de pagos (supervisor/residente/gerencia)

### 7. Historial y Reportes
- Historial individual de asistencias y pagos
- Consultas por fechas, proyectos o trabajadores
- Indicadores clave (KPIs):
  - Asistencia
  - Rendimiento
  - Costos de mano de obra
  - Avance de proyectos

### 8. Sistema de Roles y Permisos
- **Administrador**: Acceso completo al sistema
- **Supervisor**: Validación de asistencias y gestión de su proyecto
- **Trabajador**: Visualización de su información personal

---

## 🏛️ Arquitectura del Sistema

### Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                     │
├──────────────────────────┬──────────────────────────────────┤
│   Aplicación Web         │    Aplicación Móvil (Android)    │
│   (Navegador)            │    (Flet/Python)                 │
│   - Panel Admin          │    - Escaneo código barras       │
│   - Gestión completa     │    - Registro asistencia         │
│   - Reportes             │    - Validación supervisor       │
│   - Dashboards           │    - Modo Offline                │
└──────────────────────────┴──────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        CAPA DE API                           │
│                   Django REST Framework                      │
│   - Autenticación JWT                                        │
│   - Endpoints RESTful                                        │
│   - Serialización de datos                                   │
│   - Validaciones de negocio                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA DE NEGOCIO                │
│                      Aplicaciones Django                     │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  Usuarios    │  Proyectos   │ Trabajadores │  Asistencias   │
├──────────────┼──────────────┼──────────────┼────────────────┤
│  Planillas   │ Contratistas │   Reportes   │     Core       │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PERSISTENCIA                      │
│                  Base de Datos PostgreSQL                    │
│   - Usuarios y roles                                         │
│   - Proyectos y trabajadores                                 │
│   - Registros de asistencia                                  │
│   - Planillas y pagos                                        │
│   - Contratistas y contratos                                 │
└─────────────────────────────────────────────────────────────┘
```

### Patrón de Arquitectura

El sistema implementa una **arquitectura modular basada en Django Apps**, siguiendo los principios:

- **Separación de responsabilidades**: Cada app maneja un dominio específico
- **Alta cohesión, bajo acoplamiento**: Apps independientes con interfaces claras
- **DRY (Don't Repeat Yourself)**: Lógica compartida en el módulo `core`
- **Escalabilidad**: Fácil incorporación de nuevas funcionalidades
- **RESTful API**: Comunicación estándar entre frontend y backend

---

## 🛠️ Tecnologías Utilizadas

### Backend
- **Python 3.11**: Lenguaje de programación principal
- **Django 4.2 LTS**: Framework web
- **Django REST Framework**: API RESTful
- **PostgreSQL**: Base de datos relacional (SQLite en desarrollo)
- **Pillow**: Procesamiento de imágenes

### Frontend Web
- **Django Templates**: Renderizado server-side
- **Bootstrap 5**: Framework CSS
- **JavaScript/jQuery**: Interactividad

### Aplicación Móvil
- **Flet (PyFlet)**: Framework para apps móviles con Python
- **SQLite**: Base de datos local para modo offline

### Infraestructura y Deployment
- **Hostinger**: Hosting en la nube
- **Gunicorn**: Servidor WSGI
- **Nginx**: Servidor web y proxy inverso
- **Git**: Control de versiones

### Herramientas de Desarrollo
- **pytest**: Testing
- **Black**: Formateo de código
- **Flake8**: Linting
- **python-decouple**: Gestión de variables de entorno

---

## 📦 Requisitos Previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)
- Virtualenv (recomendado)
- PostgreSQL 12 o superior (producción)
- Git

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-empresa/sistema-planillas.git
cd sistema-planillas
```

### 2. Crear y activar entorno virtual

```bash
# Crear entorno virtual
python3.11 -m venv venv

# Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus configuraciones
nano .env
```

### 5. Configurar base de datos

```bash
# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### 6. Recolectar archivos estáticos

```bash
python manage.py collectstatic
```

### 7. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

El sistema estará disponible en: `http://localhost:8000`

---

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# Django
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Para PostgreSQL (producción):
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=planillas_db
# DB_USER=usuario
# DB_PASSWORD=contraseña
# DB_HOST=localhost
# DB_PORT=5432

# Seguridad
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Media y Static
MEDIA_URL=/media/
STATIC_URL=/static/

# Email (opcional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## 📁 Estructura del Proyecto

```
proyecto-planillas/
│
├── config/                           # Configuración Django
│   ├── __init__.py
│   ├── settings.py                   # Configuración principal
│   ├── urls.py                       # URLs principales
│   ├── wsgi.py                       # WSGI config
│   └── asgi.py                       # ASGI config
│
├── apps/                             # Aplicaciones Django
│   ├── __init__.py
│   │
│   ├── usuarios/                     # Gestión de usuarios
│   │   ├── models.py                 # Modelo Usuario personalizado
│   │   ├── views.py                  # Vistas y ViewSets
│   │   ├── serializers.py            # Serializers DRF
│   │   ├── urls.py                   # URLs de la app
│   │   ├── admin.py                  # Admin personalizado
│   │   ├── permissions.py            # Permisos personalizados
│   │   └── tests/                    # Tests unitarios
│   │
│   ├── proyectos/                    # Gestión de proyectos
│   │   ├── models.py                 # Modelo Proyecto
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── trabajadores/                 # Gestión de trabajadores
│   │   ├── models.py                 # Modelos: Trabajador, Asignación
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── asistencias/                  # Control de asistencia
│   │   ├── models.py                 # Modelos: Registro, Traslado
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── planillas/                    # Generación de planillas
│   │   ├── models.py                 # Modelos: Planilla, Detalle
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── utils/                    # Utilidades
│   │   │   ├── calculators.py        # Cálculos de planilla
│   │   │   └── generators.py         # Generadores de documentos
│   │   └── tests/
│   │
│   ├── contratistas/                 # Gestión de contratistas
│   │   ├── models.py                 # Modelos: Contratista, Contrato, Pago
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── reportes/                     # Sistema de reportes
│   │   ├── models.py                 # Modelo Reporte
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── utils/
│   │   │   └── exporters.py          # Exportación Excel/PDF
│   │   └── tests/
│   │
│   └── core/                         # Funcionalidades compartidas
│       ├── models.py                 # Modelos base abstractos
│       ├── permissions.py            # Permisos base
│       ├── pagination.py             # Paginación personalizada
│       ├── exceptions.py             # Excepciones custom
│       └── utils.py                  # Utilidades generales
│
├── media/                            # Archivos subidos
│   ├── documentos/
│   ├── soportes/
│   └── codigos_barras/
│
├── static/                           # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
│
├── templates/                        # Templates HTML
│   ├── admin/
│   └── reportes/
│
├── manage.py                         # CLI Django
├── requirements.txt                  # Dependencias Python
├── .env                              # Variables de entorno
├── .env.example                      # Ejemplo de .env
├── .gitignore                        # Git ignore
└── README.md                         # Este archivo
```

---

## 🗄️ Modelo de Datos

### Entidades Principales

#### 1. Usuarios
- Gestión de usuarios del sistema
- Roles: Administrador, Supervisor, Trabajador
- Autenticación y autorización

#### 2. Proyectos
- Información del proyecto de construcción
- Geolocalización
- Control de fechas y avance
- Presupuesto vs. gasto real

#### 3. Trabajadores
- Datos personales del trabajador
- Cargo y tarifas
- Código de barras para identificación
- Proyecto actual asignado

#### 4. Asignaciones de Proyecto
- Historial de asignaciones trabajador-proyecto
- Control de fechas de asignación/desasignación

#### 5. Registros de Asistencia
- Entrada y salida diaria
- Validación por supervisor
- Cálculo de horas trabajadas y extras

#### 6. Traslados
- Movimiento de trabajadores entre proyectos
- Registro de autorización y motivo

#### 7. Planillas
- Generación automática de planillas
- Período de pago
- Estado (borrador, aprobada, pagada)

#### 8. Detalle de Planilla
- Información detallada por trabajador
- Cálculos de horas, bonos, deducciones
- Total a pagar

#### 9. Contratistas
- Información del contratista
- Especialidad y datos de contacto

#### 10. Contratos
- Condiciones del contrato
- Actividades y unidades de medida
- Valor total y fechas

#### 11. Pagos a Contratistas
- Registro de pagos progresivos
- Porcentaje ejecutado
- Aprobación por niveles

#### 12. Historial de Pagos
- Registro histórico de todos los pagos
- Método de pago y comprobantes

### Diagrama ERD

Ver diagrama completo en: `docs/database/ERD.png`

**Relaciones principales:**
- Usuario (1) → (N) Proyectos (como supervisor)
- Proyecto (1) → (N) Trabajadores (proyecto actual)
- Trabajador (N) ↔ (M) Proyecto (a través de Asignaciones)
- Trabajador (1) → (N) Registros de Asistencia
- Proyecto (1) → (N) Registros de Asistencia
- Proyecto (1) → (N) Planillas
- Planilla (1) → (N) Detalle de Planilla
- Contratista (1) → (N) Contratos
- Proyecto (1) → (N) Contratos
- Contrato (1) → (N) Pagos

---

## 🌐 API Endpoints

### Autenticación
```
POST   /api/auth/login/              # Iniciar sesión
POST   /api/auth/logout/             # Cerrar sesión
POST   /api/auth/refresh/            # Refrescar token
GET    /api/auth/me/                 # Información del usuario actual
```

### Usuarios
```
GET    /api/usuarios/                # Listar usuarios
POST   /api/usuarios/                # Crear usuario
GET    /api/usuarios/{id}/           # Detalle de usuario
PUT    /api/usuarios/{id}/           # Actualizar usuario
DELETE /api/usuarios/{id}/           # Eliminar usuario
```

### Proyectos
```
GET    /api/proyectos/               # Listar proyectos
POST   /api/proyectos/               # Crear proyecto
GET    /api/proyectos/{id}/          # Detalle de proyecto
PUT    /api/proyectos/{id}/          # Actualizar proyecto
DELETE /api/proyectos/{id}/          # Eliminar proyecto
GET    /api/proyectos/{id}/trabajadores/  # Trabajadores del proyecto
GET    /api/proyectos/{id}/avance/   # Avance del proyecto
```

### Trabajadores
```
GET    /api/trabajadores/            # Listar trabajadores
POST   /api/trabajadores/            # Crear trabajador
GET    /api/trabajadores/{id}/       # Detalle de trabajador
PUT    /api/trabajadores/{id}/       # Actualizar trabajador
DELETE /api/trabajadores/{id}/       # Eliminar trabajador
POST   /api/trabajadores/{id}/trasladar/  # Trasladar trabajador
GET    /api/trabajadores/{id}/historial/  # Historial del trabajador
```

### Asistencias
```
GET    /api/asistencias/             # Listar asistencias
POST   /api/asistencias/             # Registrar asistencia
GET    /api/asistencias/{id}/        # Detalle de asistencia
PUT    /api/asistencias/{id}/        # Actualizar asistencia
POST   /api/asistencias/{id}/validar/  # Validar asistencia
GET    /api/asistencias/pendientes/  # Asistencias pendientes de validar
POST   /api/asistencias/escanear/    # Registrar por código de barras
```

### Planillas
```
GET    /api/planillas/               # Listar planillas
POST   /api/planillas/generar/       # Generar planilla
GET    /api/planillas/{id}/          # Detalle de planilla
PUT    /api/planillas/{id}/          # Actualizar planilla
POST   /api/planillas/{id}/aprobar/  # Aprobar planilla
GET    /api/planillas/{id}/exportar/ # Exportar planilla (Excel/PDF)
GET    /api/planillas/{id}/denominaciones/  # Denominaciones bancarias
```

### Contratistas
```
GET    /api/contratistas/            # Listar contratistas
POST   /api/contratistas/            # Crear contratista
GET    /api/contratistas/{id}/       # Detalle de contratista
PUT    /api/contratistas/{id}/       # Actualizar contratista
GET    /api/contratistas/{id}/contratos/  # Contratos del contratista
POST   /api/contratistas/{id}/contratos/  # Crear contrato
POST   /api/contratos/{id}/pagos/    # Registrar pago
POST   /api/pagos/{id}/aprobar/      # Aprobar pago
```

### Reportes
```
GET    /api/reportes/asistencia/     # Reporte de asistencia
GET    /api/reportes/costos/         # Reporte de costos
GET    /api/reportes/rendimiento/    # Reporte de rendimiento
GET    /api/reportes/proyecto/{id}/  # Reporte por proyecto
GET    /api/reportes/trabajador/{id}/ # Reporte por trabajador
POST   /api/reportes/personalizado/  # Reporte personalizado
```

---

## 🧪 Testing

### Ejecutar todos los tests

```bash
python manage.py test
```

### Ejecutar tests de una app específica

```bash
python manage.py test apps.usuarios
```

### Ejecutar con pytest (recomendado)

```bash
pytest
```

### Cobertura de código

```bash
pytest --cov=apps --cov-report=html
```

---

## 🚢 Deployment

### Preparación para producción

1. **Configurar variables de entorno de producción**
```bash
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
SECRET_KEY=tu-secret-key-segura
```

2. **Configurar PostgreSQL**
```bash
DB_ENGINE=django.db.backends.postgresql
DB_NAME=planillas_prod
DB_USER=usuario_prod
DB_PASSWORD=contraseña_segura
DB_HOST=localhost
DB_PORT=5432
```

3. **Recolectar archivos estáticos**
```bash
python manage.py collectstatic --noinput
```

4. **Ejecutar migraciones**
```bash
python manage.py migrate
```

5. **Configurar Gunicorn**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Deployment en Hostinger

Ver guía detallada en: `docs/deployment/hostinger.md`

---

## 🤝 Contribución

Este proyecto es de uso interno de la empresa. Para contribuir:

1. Crear una rama desde `develop`
2. Realizar los cambios necesarios
3. Escribir/actualizar tests
4. Enviar Pull Request a `develop`
5. Esperar revisión del equipo

### Estándares de código

- Seguir PEP 8
- Usar Black para formateo
- Documentar funciones y clases
- Mantener cobertura de tests >80%

---

## 📄 Licencia

Copyright © 2025 [Nombre de la Empresa]. Todos los derechos reservados.

Este software es propiedad de [Nombre de la Empresa] y está protegido por las leyes de derechos de autor. El código fuente se entrega al cliente con opción de instalación en servidor propio, pero sin derecho de redistribución.

---

## 📞 Contacto y Soporte

- **Equipo de Desarrollo**: jhonstmedinav@gmail.com
- **Soporte Técnico**: jhonstmedinav@gmail.com

---

## 📝 Notas Adicionales

### Características Destacadas

✅ **Sin dependencia de licencias externas**: El cliente recibe el código fuente completo  
✅ **Funcionalidad offline**: La app móvil funciona sin conexión y sincroniza después  
✅ **Trazabilidad completa**: Historial detallado de todos los movimientos  
✅ **Validación diaria**: Los supervisores aprueban las asistencias diariamente  
✅ **Traslados flexibles**: Los trabajadores pueden moverse entre proyectos  
✅ **Escalable**: Arquitectura modular lista para futuras integraciones  
✅ **Seguro**: Control de acceso por roles y permisos  

### Próximas Funcionalidades (Roadmap)

- [ ] Integración con inventario de herramientas y materiales
- [ ] Control de costos de obra integrado
- [ ] Indicadores de eficiencia de proyecto
- [ ] Notificaciones push en tiempo real
- [ ] Dashboard ejecutivo con BI
- [ ] App iOS con Flutter/Flet

---

**Versión**: 1.0.0  
**Última actualización**: Octubre 2025  
**Estado**: En Desarrollo