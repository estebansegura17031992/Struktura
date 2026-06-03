# Kanban MVP — Backend

API REST construida con **FastAPI + PostgreSQL + SQLAlchemy async**.  
Parte del sistema Kanban MVP · PRD v2 · Stack: FastAPI · PostgreSQL · Alembic · JWT · structlog · Railway.

---

## Tabla de contenidos

1. [Prerrequisitos](#1-prerrequisitos)
2. [Variables de entorno](#2-variables-de-entorno)
3. [Setup local](#3-setup-local)
4. [Ejecutar tests](#4-ejecutar-tests)
5. [Estructura del proyecto](#5-estructura-del-proyecto)
6. [Arquitectura y decisiones clave](#6-arquitectura-y-decisiones-clave)
7. [Endpoints públicos y protegidos](#7-endpoints-públicos-y-protegidos)
8. [Paginación](#8-paginación)
9. [Formato de errores](#9-formato-de-errores)
10. [Logs estructurados](#10-logs-estructurados)
11. [Deploy en Railway](#11-deploy-en-railway)
12. [Deuda técnica documentada](#12-deuda-técnica-documentada)
13. [Convenciones de desarrollo](#13-convenciones-de-desarrollo)

---

## 1. Prerrequisitos

| Herramienta | Versión mínima | Notas |
|---|---|---|
| Python | 3.11 | Usar `pyenv` o el instalador oficial |
| pip | Incluido con Python 3.11 | |
| PostgreSQL | 15 | Local o cuenta en [Supabase](https://supabase.com) |
| Git | cualquiera | |

> **Windows:** Se recomienda usar WSL2 (Ubuntu 22.04+). Los comandos de esta guía asumen un terminal Unix.

Generar un `JWT_SECRET` seguro antes de continuar:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Variables de entorno

Copia el archivo de ejemplo y edítalo con tus valores reales:

```bash
cp .env.example .env
```

> **Nunca hagas commit de `.env`.** Ya está en `.gitignore`.

### Referencia completa de variables

```bash
# ─── Aplicación ───────────────────────────────────────────
ENVIRONMENT=dev
# dev   → stack traces en responses, ENABLE_DOCS forzado a true
# prod  → stack traces ocultos, logs JSON a stdout

ENABLE_DOCS=true
# true  → Swagger UI en /docs y /redoc (solo para desarrollo)
# false → deshabilitar en producción

# ─── Base de datos ────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kanban_db
# Supabase example:
# DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Solo para la suite de tests de integración (base de datos separada)
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kanban_test

# ─── JWT ──────────────────────────────────────────────────
JWT_SECRET=reemplaza-con-secreto-de-al-menos-32-caracteres
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── Email (Resend) ───────────────────────────────────────
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=noreply@tudominio.com
# En desarrollo local usa Mailtrap para no consumir cuota de Resend:
# RESEND_API_KEY=tu-api-key-de-mailtrap

# ─── CORS ─────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173
# ⚠ Debe coincidir exactamente con el origen del frontend (incluido el puerto).
# Nunca usar * cuando se envían cookies (credentials: "include").
# Producción: CORS_ORIGINS=https://tu-app.vercel.app

# ─── Rate limiting ────────────────────────────────────────
RATE_LIMIT_ENABLED=true
# false útil para tests de integración que no deban preocuparse por límites
```

### `.env.example` (archivo a commitear en el repo)

```bash
ENVIRONMENT=dev
ENABLE_DOCS=true
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kanban_db
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kanban_test
JWT_SECRET=
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
RESEND_API_KEY=
EMAIL_FROM=noreply@example.com
CORS_ORIGINS=http://localhost:5173
RATE_LIMIT_ENABLED=true
```

---

## 3. Setup local

Tiempo estimado: **menos de 5 minutos** desde cero.

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/tu-org/kanban-backend.git
cd kanban-backend
```

### Paso 2 — Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate        # Windows WSL: misma instrucción
                                  # Windows CMD: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Paso 3 — Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus valores reales.
# Como mínimo necesitas: DATABASE_URL, JWT_SECRET, RESEND_API_KEY
```

### Paso 4 — Crear la base de datos

**Opción A — PostgreSQL local:**

```bash
createdb kanban_db
# Si psql pide usuario: createdb -U postgres kanban_db
```

**Opción B — Supabase (free tier):**

1. Crea un proyecto en [supabase.com](https://supabase.com)
2. Ve a **Settings → Database → Connection string → URI**
3. Selecciona el modo **Transaction pooler** (puerto 6543)
4. Copia la URL y reemplaza `[YOUR-PASSWORD]` con tu contraseña
5. Pégala en `DATABASE_URL` de tu `.env`

### Paso 5 — Aplicar migraciones

```bash
alembic upgrade head
```

Verifica que las tablas se crearon correctamente:

```bash
psql kanban_db -c "\dt"
# Deberías ver: users, refresh_tokens, email_verifications,
#               password_reset_tokens, system_settings, audit_logs
```

Si usas Supabase, conecta con el connection string de **Direct connection** (puerto 5432) para las migraciones:

```bash
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[pw]@db.[ref].supabase.co:5432/postgres alembic upgrade head
```

### Paso 6 — Levantar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

### Paso 7 — Verificar que todo funciona

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "db": "connected",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

Swagger UI disponible en: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Ejecutar tests

### Preparar la base de datos de tests

```bash
createdb kanban_test
# Asegúrate de que TEST_DATABASE_URL en .env apunte a kanban_test
```

### Comandos

```bash
# Todos los tests
pytest

# Solo tests unitarios (sin necesidad de DB, rápidos)
pytest tests/unit/ -v

# Solo tests de integración (requieren DB activa)
pytest tests/integration/ -v

# Un módulo específico
pytest tests/integration/test_auth.py -v

# Con reporte de cobertura
pytest --cov=app --cov-report=term-missing

# Generar reporte HTML de cobertura
pytest --cov=app --cov-report=html
# Abre htmlcov/index.html en el navegador

# Ejecutar tests en paralelo (requiere pytest-xdist)
pytest -n auto
```

### Cobertura mínima por módulo

| Módulo | Cobertura mínima | Notas |
|---|---|---|
| `app/services/` | 85% | Lógica de negocio crítica |
| `app/core/security.py` | 90% | JWT, bcrypt, tokens |
| `app/repositories/` | 75% | Queries a DB |
| `app/routers/` | 70% | Cubierto principalmente por integración |

### Variables de entorno para tests

Los tests de integración leen `TEST_DATABASE_URL`. Si la variable no existe, `pytest` falla con un error descriptivo antes de ejecutar cualquier test. Esto previene que los tests modifiquen la base de datos de desarrollo por accidente.

---

## 5. Estructura del proyecto

```
kanban-backend/
│
├── app/
│   ├── main.py                  # Entry point: registra routers, middleware y exception handlers
│   ├── config.py                # Configuración via pydantic-settings (lee .env)
│   ├── database.py              # Engine async, SessionLocal, Base declarativa
│   ├── dependencies.py          # get_db, get_current_user, require_role(), verify_project_membership()
│   │
│   ├── models/                  # SQLAlchemy ORM models (fuente de verdad del schema)
│   │   ├── __init__.py
│   │   ├── user.py              # User, enums de rol
│   │   ├── token.py             # RefreshToken, EmailVerification, PasswordResetToken
│   │   ├── project.py           # Project, ProjectMember
│   │   ├── task.py              # Task, TaskAssignee
│   │   ├── timer.py             # TaskTimeEntry
│   │   ├── comment.py           # Comment, CommentMention
│   │   ├── audit.py             # AuditLog
│   │   └── settings.py          # SystemSetting
│   │
│   ├── schemas/                 # Pydantic schemas: DTOs de request y response
│   │   ├── __init__.py
│   │   ├── auth.py              # LoginRequest, TokenResponse, RegisterRequest...
│   │   ├── user.py              # UserResponse, UserUpdate...
│   │   ├── project.py           # ProjectCreate, ProjectResponse, MemberResponse...
│   │   ├── task.py              # TaskCreate, TaskResponse, TaskFilter...
│   │   ├── pagination.py        # PaginatedResponse[T] genérico
│   │   └── errors.py            # ErrorResponse, ErrorDetail
│   │
│   ├── repositories/            # Capa de acceso a datos — solo queries, sin lógica de negocio
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── token_repository.py
│   │   ├── project_repository.py
│   │   ├── task_repository.py
│   │   └── audit_repository.py
│   │
│   ├── services/                # Lógica de negocio — orquesta repositories, valida reglas
│   │   ├── __init__.py
│   │   ├── auth_service.py      # register, login, refresh, logout, verify_email
│   │   ├── password_service.py  # forgot_password, reset_password
│   │   ├── user_service.py      # get_users, update_role, update_profile
│   │   ├── project_service.py   # CRUD proyectos, membresía, ownership
│   │   ├── task_service.py      # CRUD tareas, asignación, filtros
│   │   ├── timer_service.py     # start, stop, historial
│   │   └── email_service.py     # Wrapper de Resend con plantillas
│   │
│   ├── routers/                 # Endpoints FastAPI — delegan al service, sin lógica propia
│   │   ├── __init__.py
│   │   ├── auth.py              # /auth/*
│   │   ├── users.py             # /users/me, /admin/users
│   │   ├── projects.py          # /projects/*
│   │   ├── tasks.py             # /tasks/*
│   │   ├── timers.py            # /tasks/{id}/timer
│   │   ├── comments.py          # /tasks/{id}/comments
│   │   ├── dashboard.py         # /dashboard
│   │   ├── admin.py             # /admin/audit-logs, /admin/settings
│   │   └── health.py            # /health
│   │
│   └── core/
│       ├── security.py          # JWT encode/decode, bcrypt hash/verify
│       ├── exceptions.py        # AppBaseError base + exception handlers globales
│       ├── logging.py           # Configuración de structlog
│       ├── pagination.py        # Helper paginate(query, page, page_size)
│       └── rate_limiter.py      # slowapi, límites por endpoint
│
├── alembic/
│   ├── env.py                   # Lee DATABASE_URL de config, importa todos los models
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py   # Migración inicial: todas las tablas + ENUMs
│
├── tests/
│   ├── conftest.py              # Fixtures: db session, client HTTP, usuarios de prueba
│   ├── unit/
│   │   ├── test_security.py     # JWT, bcrypt, generación de tokens
│   │   ├── test_pagination.py   # Helper de paginación
│   │   └── test_validators.py   # Validaciones de schemas Pydantic
│   └── integration/
│       ├── test_auth.py         # register, verify, login, refresh, logout, reset
│       ├── test_users.py        # perfil, cambio de rol, gestión admin
│       ├── test_projects.py     # CRUD, límite, membresía, historial, ownership
│       ├── test_tasks.py        # CRUD, filtros, asignación múltiple
│       ├── test_timers.py       # start/stop, reglas de negocio
│       └── test_permissions.py  # Matriz de acceso por rol (tabla de verdad)
│
├── .env.example                 # Plantilla de variables de entorno (sin valores reales)
├── .gitignore
├── alembic.ini                  # Apunta sqlalchemy.url a %(DATABASE_URL)s
├── entrypoint.sh                # Railway: alembic upgrade head && uvicorn ...
├── requirements.txt
├── requirements-dev.txt         # pytest, httpx, pytest-asyncio, coverage
└── README.md
```

---

## 6. Arquitectura y decisiones clave

### Patrón de capas

```
Router → Service → Repository → Database
          ↑
     Dependencies
   (get_db, require_role,
    verify_project_membership)
```

- **Router:** solo recibe request, llama al service y retorna response. Sin lógica de negocio.
- **Service:** valida reglas de negocio, orquesta múltiples repositories, lanza excepciones de dominio.
- **Repository:** ejecuta queries SQLAlchemy. Recibe una `AsyncSession`, nunca la crea.
- **Dependencies:** inyectadas por FastAPI. `get_current_user` decodifica el JWT. `require_role(*roles)` valida permisos. `verify_project_membership(project_id, user_id)` valida membresía activa.

### Decisiones de arquitectura cerradas (ADR)

| ID | Decisión | Impacto |
|---|---|---|
| **ADR-01** | Refresh token **sin rotación** en MVP | Evita race condition multi-tab. Deuda técnica: migrar a rotación con Redis en post-MVP. |
| **ADR-02** | Sin notificaciones en tiempo real en MVP | La tabla `comment_mentions` persiste los datos; solo falta la tabla `notifications` en post-MVP. |
| **ADR-03** | Timer bloqueado si la tarea tiene múltiples asignados | Regla de negocio pendiente de definición para cronómetros compartidos. |

### Acuerdos de negocio

| ID | Regla |
|---|---|
| **AG-01** | El primer usuario registrado (cuando `COUNT(users) = 0`) obtiene rol `admin` automáticamente. |
| **AG-02** | Timezone detectada por el frontend con `Intl.DateTimeFormat().resolvedOptions().timeZone`. Fallback: UTC. |
| **AG-03** | No se puede cambiar email ni username en el MVP. Solo nombre completo y timezone. |
| **AG-04** | Soft delete para proyectos y tareas. Los registros nunca se eliminan físicamente. |
| **AG-05** | Un usuario no puede tener más de un cronómetro activo simultáneamente. |

### Roles del sistema

```
Sistema (users.role):
  viewer  → ve tareas propias, filtros propios, dashboard propio
  editor  → todo anterior + CRUD tareas y proyectos, asignar usuarios
  admin   → acceso total + gestión usuarios + detener timers ajenos + editar cualquier comentario

Proyecto (project_members.role):
  owner   → control total del proyecto + transferencia de ownership
  editor  → CRUD de tareas y miembros dentro del proyecto
  viewer  → solo lectura dentro del proyecto

Regla de precedencia: se aplica el rol más restrictivo entre sistema y proyecto.
```

### Seguridad

- `JWT_SECRET` mínimo 32 caracteres. Access token: 15 min. Refresh token: 7 días (cookie HttpOnly, SameSite=Lax, Secure, Path=/auth/refresh).
- Contraseñas hasheadas con **bcrypt, cost ≥ 12**. Nunca en logs ni en responses.
- CORS: `allow_credentials=True`, `allow_origins` nunca puede ser `*`. Configurado via `CORS_ORIGINS`.
- Headers de seguridad HTTP: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin`.
- Rate limiting: 5 intentos/IP/15 min en `/auth/login` y `/auth/register`. 3 solicitudes/IP/15 min en `/auth/forgot-password`. Responde 429 con header `Retry-After`.
- Stack traces **ocultos** en `ENVIRONMENT=prod`. Swagger UI deshabilitado con `ENABLE_DOCS=false`.

---

## 7. Endpoints públicos y protegidos

Los siguientes endpoints **no** requieren token JWT:

```
POST   /auth/register
POST   /auth/verify-email
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout
POST   /auth/forgot-password
POST   /auth/reset-password
GET    /health
GET    /docs          (solo si ENABLE_DOCS=true)
GET    /redoc         (solo si ENABLE_DOCS=true)
GET    /openapi.json  (solo si ENABLE_DOCS=true)
```

Todos los demás endpoints requieren el header:

```
Authorization: Bearer <access_token>
```

---

## 8. Paginación

Todos los endpoints de lista usan el mismo patrón:

**Query params:**

| Param | Default | Máximo |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 20 | 100 (50 para columnas Kanban) |

Si `page_size` excede el máximo, se clampea y el response incluye `page_size_applied`.

**Response wrapper:**

```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "page_size_applied": 20,
  "total": 87,
  "total_pages": 5,
  "next_page": 2,
  "previous_page": null
}
```

---

## 9. Formato de errores

Todos los errores siguen la misma estructura, sin importar el origen:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email o contraseña incorrectos.",
    "details": null
  }
}
```

Errores de validación Pydantic incluyen `details` con el campo que falló:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Error de validación en la solicitud.",
    "details": [
      {
        "field": "password",
        "message": "La contraseña debe tener al menos 8 caracteres y un número."
      }
    ]
  }
}
```

**Nunca** se expone un stack trace en producción. En `ENVIRONMENT=dev` el campo `details` puede incluir información adicional de depuración.

### Códigos de error comunes

| Código HTTP | `error.code` | Situación |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Datos de entrada inválidos |
| 400 | `EMAIL_NOT_VERIFIED` | Intento de login con email no verificado |
| 400 | `INVALID_VERIFICATION_CODE` | Código expirado o incorrecto |
| 401 | `UNAUTHORIZED` | Token ausente o inválido |
| 401 | `INVALID_CREDENTIALS` | Email o contraseña incorrectos |
| 403 | `FORBIDDEN` | Rol insuficiente para la operación |
| 404 | `NOT_FOUND` | Recurso no existe o no es accesible |
| 409 | `EMAIL_ALREADY_EXISTS` | Email duplicado en registro |
| 409 | `USERNAME_ALREADY_EXISTS` | Username duplicado |
| 409 | `PROJECT_LIMIT_REACHED` | Límite de proyectos por usuario alcanzado |
| 409 | `TIMER_ALREADY_RUNNING` | El usuario ya tiene un cronómetro activo |
| 410 | `TOKEN_ALREADY_USED` | Token de reset usado o expirado |
| 422 | `CANNOT_REMOVE_LAST_ADMIN` | Operación dejaría el sistema sin admins |
| 429 | `RATE_LIMIT_EXCEEDED` | Demasiados intentos. Ver header `Retry-After` |

---

## 10. Logs estructurados

La aplicación usa `structlog` para emitir logs en formato JSON a stdout. Railway los captura automáticamente.

**Formato de cada línea de log:**

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "info",
  "event": "auth.login.success",
  "user_id": "usr_01HXK3...",
  "request_id": "req_9fBz1...",
  "path": "/auth/login",
  "status_code": 200,
  "duration_ms": 142
}
```

**Reglas:**

- Nunca incluir `password`, `token`, `api_key` ni ningún secreto en los logs.
- En `ENVIRONMENT=dev` los logs se formatean en texto legible para terminal.
- En `ENVIRONMENT=prod` los logs son JSON puros (Railway los indexa correctamente).

---

## 11. Deploy en Railway

### Archivos necesarios

**`entrypoint.sh`** (en la raíz del proyecto):

```bash
#!/bin/sh
set -e

echo "Aplicando migraciones..."
alembic upgrade head

echo "Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

```bash
chmod +x entrypoint.sh
```

**`Procfile`** (alternativa a entrypoint.sh):

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Variables de entorno en Railway

Configurar en **Railway → Project → Variables**:

```
ENVIRONMENT=prod
ENABLE_DOCS=false
DATABASE_URL=<connection string de Supabase — Transaction pooler>
JWT_SECRET=<secreto generado con secrets.token_hex(32)>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
RESEND_API_KEY=<api key de Resend>
EMAIL_FROM=noreply@tudominio.com
CORS_ORIGINS=https://tu-app.vercel.app
RATE_LIMIT_ENABLED=true
```

> ⚠ `DATABASE_URL` en producción debe usar el **Transaction pooler** de Supabase (puerto 6543) para respetar el límite de conexiones del free tier (~60 conexiones). Para las migraciones usar el Direct connection (puerto 5432) — Railway lo ejecuta una sola vez al deploy.

### Consideraciones de infraestructura

| Servicio | Plan | Límites |
|---|---|---|
| Railway (backend) | Hobby free | 512 MB RAM, 1 instancia |
| Supabase (PostgreSQL) | Free | 500 MB storage, ~60 conexiones |
| Vercel (frontend) | Hobby free | Sin límite de requests |
| Resend (email) | Free | 3,000 emails/mes |

Pool de conexiones SQLAlchemy configurado para respetar el límite de Supabase:

```python
# app/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
)
```

---

## 12. Deuda técnica documentada

Decisiones tomadas conscientemente para el MVP. No implementar sin consenso del equipo.

| ID | Descripción | Sprint origen | Para resolver |
|---|---|---|---|
| **DT-01** | Rate limiter con `slowapi` almacena estado en memoria. No funciona con múltiples instancias. | S1 | Migrar a Redis + `slowapi` con backend Redis en post-MVP. |
| **DT-02** | Refresh token sin rotación (ADR-01). Race condition posible si se escala horizontalmente con rotación activada. | S1 | Implementar rotación con grace period usando Redis. |
| **DT-03** | APScheduler corre en el mismo proceso de FastAPI (job de limpieza de tokens expirados). No sobrevive a múltiples instancias. | S1 | Migrar a job externo (Railway Cron o Celery) en post-MVP. |
| **DT-04** | Regla de cronómetro bloqueada para tareas con múltiples asignados (ADR-03). | S2 | Definir estrategia de distribución de tiempo en tareas compartidas. |
| **DT-05** | FTS (Full Text Search) usa diccionario `'spanish'`. No soporta contenido multiidioma. | S3 | Cambiar a `'simple'` o implementar columna `search_vector` multiidioma. |

---

## 13. Convenciones de desarrollo

### Ramas

```
main          → producción (Railway deploya desde aquí)
develop       → integración de features
feature/xxx   → nueva funcionalidad
fix/xxx       → corrección de bug
```

### Pull Requests

Un PR no puede mergearse si:

- El pipeline CI falla (lint + tests)
- Hay secrets hardcodeados detectados (git-secrets o trufflehog)
- Falta al menos un revisor aprobador del área responsable
- Los tests de integración del módulo modificado no tienen cobertura del happy path **y** al menos un error path

### Definition of Done

Un artefacto se considera **Done** cuando:

1. PR aprobado por al menos un revisor del área responsable
2. Tests de integración: happy path + al menos un error path en CI verde
3. Endpoint documentado en el OpenAPI generado automáticamente por FastAPI
4. Sin secrets hardcodeados ni en código ni en logs
5. Funciona en el entorno de desarrollo compartido (no solo en local del desarrollador)

### Comandos útiles del día a día

```bash
# Crear nueva migración después de modificar un modelo
alembic revision --autogenerate -m "descripcion_corta"

# Ver historial de migraciones aplicadas
alembic history --verbose

# Revertir la última migración (con cuidado en entornos compartidos)
alembic downgrade -1

# Linting
ruff check app/
ruff format app/

# Type checking
mypy app/

# Ver logs del servidor en formato legible (dev)
uvicorn app.main:app --reload | python -m structlog_pretty
```

---

## Epicas cubiertas por sprint

| Sprint | Épicas | Estado |
|---|---|---|
| S1 | E01 Auth + E09 Infra base | ✅ |
| S2 | E02 Roles + E03 Proyectos (sin invitaciones) | 🔄 En progreso |
| S3 | E04 Tareas y Kanban | ⏳ |
| S4 | E05 Cronómetro + E03 Invitaciones | ⏳ |
| S5 | E06 Dashboard + E07 Comentarios | ⏳ |
| S6 | E08 Auditoría + E09 Admin + E02 Admin | ⏳ |
| S7 | QA + Deploy producción | ⏳ |

---

*Kanban MVP Backend · PRD v2 · FastAPI · PostgreSQL · Railway · 56 requerimientos · 9 épicas*
