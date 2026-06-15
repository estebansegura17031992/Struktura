# Struktura — Kanban MVP

> **Stack:** FastAPI · PostgreSQL · React + Vite · Tailwind CSS  
> **Versión API:** `0.2.0` · **Sprint actual:** 2 (E02 + E03)  
> **CI:** [![CI](https://github.com/estebansegura17031992/Struktura/actions/workflows/ci.yml/badge.svg?branch=staging)](https://github.com/estebansegura17031992/Struktura/actions)

---

## Índice

1. [Setup local](#1-setup-local)
2. [Variables de entorno](#2-variables-de-entorno)
3. [Endpoints — Sprint 1 (E01 Auth)](#3-endpoints-sprint-1-e01-auth)
4. [Endpoints — Sprint 2 (E02 Roles + E03 Proyectos)](#4-endpoints-sprint-2-e02-roles--e03-proyectos)
5. [RBAC — Tabla de permisos](#5-rbac--tabla-de-permisos)
6. [Audit logs](#6-audit-logs)
7. [Ejecutar tests](#7-ejecutar-tests)
8. [Deuda técnica documentada](#8-deuda-técnica-documentada)

---

## 1. Setup local

### Prerrequisitos

- Python 3.11+
- Node 18+
- PostgreSQL 15+

### Backend

```bash
git clone https://github.com/estebansegura17031992/Struktura.git
cd Struktura/backend

python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Aplicar migraciones
alembic upgrade head

# Levantar servidor
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd Struktura/frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 2. Variables de entorno

Crea `backend/.env` copiando desde `backend/.env.example`:

### Sprint 1 (base)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Conexión asyncpg | `postgresql+asyncpg://user:pass@localhost:5432/kanban_db` |
| `DATABASE_URL_SYNC` | Conexión psycopg2 para Alembic | `postgresql+psycopg2://user:pass@localhost:5432/kanban_db` |
| `JWT_SECRET` | Clave secreta para firmar JWT | `super-secret-key-min-32-chars` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Duración access token | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Duración refresh token | `30` |
| `FRONTEND_URL` | URL del frontend (CORS + emails) | `http://localhost:5173` |
| `EMAIL_DEV_MODE` | Imprime emails en consola si `true` | `true` |
| `ENABLE_DOCS` | Activa `/docs` y `/redoc` | `true` |
| `ENVIRONMENT` | Entorno de ejecución | `development` |
| `RATE_LIMIT_ENABLED` | Activa rate limiting | `false` |

### Sprint 2 (nuevas)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `APP_VERSION` | Versión de la API | `0.2.0` |
| `TEST_DATABASE_URL` | DB para tests (asyncpg) | `postgresql+asyncpg://user:pass@localhost:5432/kanban_test` |

---

## 3. Endpoints — Sprint 1 (E01 Auth)

Base URL: `/api/v1`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/auth/register` | ✗ | Registro de usuario |
| `POST` | `/auth/verify-email` | ✗ | Verificación de email con código |
| `POST` | `/auth/resend-verification` | ✗ | Reenvío de código de verificación |
| `POST` | `/auth/login` | ✗ | Login — retorna access token + cookie refresh |
| `POST` | `/auth/refresh` | Cookie | Silent refresh del access token |
| `POST` | `/auth/logout` | ✓ | Revoca refresh token |
| `POST` | `/auth/forgot-password` | ✗ | Solicita reset de contraseña (envía email) |
| `POST` | `/auth/reset-password` | ✗ | Restablece contraseña con token de un solo uso |
| `GET` | `/users/me` | ✓ | Perfil del usuario autenticado |
| `PATCH` | `/users/me` | ✓ | Actualizar perfil |
| `GET` | `/users/me/sessions` | ✓ | Sesiones activas |
| `DELETE` | `/users/me/sessions/{id}` | ✓ | Revocar sesión específica |
| `GET` | `/health` | ✗ | Health check |

---

## 4. Endpoints — Sprint 2 (E02 Roles + E03 Proyectos)

### E02 · Administración de usuarios y roles

Todos los endpoints `/admin/*` requieren rol `admin`.

| Método | Ruta | Descripción | Errores |
|---|---|---|---|
| `GET` | `/admin/users` | Listado paginado de usuarios. Query params: `page`, `page_size`, `search`, `role` | `403` |
| `PATCH` | `/admin/users/{user_id}/role` | Cambiar rol del usuario. Body: `{ role: "admin\|editor\|viewer" }` | `403` `404` `422 CANNOT_REMOVE_LAST_ADMIN` |

### E03 · Gestión de proyectos

Todos los endpoints `/projects/*` requieren autenticación JWT. Los endpoints de proyecto específico también requieren membresía activa.

#### CRUD de proyectos

| Método | Ruta | Roles permitidos | Descripción | Errores |
|---|---|---|---|---|
| `POST` | `/projects` | `editor` `admin` | Crear proyecto. El creador queda como `owner` | `403` `422 PROJECT_LIMIT_REACHED` |
| `GET` | `/projects` | Cualquier rol | Listar proyectos del usuario. Incluye `my_role` y `member_count` | `403` |
| `PATCH` | `/projects/{id}` | `owner` `admin` | Editar nombre o descripción | `403` `404` |
| `DELETE` | `/projects/{id}` | `owner` `admin` | Soft delete. Rechaza si hay tareas activas | `403` `404` `409 PROJECT_HAS_ACTIVE_TASKS` |

#### Gestión de miembros

| Método | Ruta | Roles permitidos | Descripción | Errores |
|---|---|---|---|---|
| `GET` | `/projects/{id}/members` | Cualquier miembro | Lista miembros activos con datos de usuario | `403` `404` |
| `POST` | `/projects/{id}/members` | `owner` `editor` | Agregar miembro. Editor no puede asignar rol `owner` | `403` `404` `409 MEMBER_ALREADY_EXISTS` |
| `DELETE` | `/projects/{id}/members/{uid}` | `owner` `editor` | Remover miembro (soft delete con `removed_at`) | `403` `404` `409 CANNOT_REMOVE_OWNER` |
| `GET` | `/projects/{id}/members/history` | `owner` `editor` `admin` | Historial completo de membresías (activas + removidas) | `403` `404` |
| `POST` | `/projects/{id}/transfer-ownership` | `owner` | Transferencia atómica de ownership. El nuevo owner debe ser miembro activo | `403` `404` `409 INVALID_OPERATION` |

### Respuesta estándar de proyecto (`ProjectResponse`)

```json
{
  "id": "uuid",
  "name": "Nombre del proyecto",
  "description": "Descripción opcional",
  "owner_id": "uuid",
  "created_at": "2026-06-01T00:00:00+00:00",
  "updated_at": "2026-06-01T00:00:00+00:00",
  "my_role": "owner | editor | viewer | admin",
  "member_count": 4
}
```

### Respuesta estándar de miembro (`MemberResponse`)

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "user_id": "uuid",
  "role": "owner | editor | viewer",
  "joined_at": "2026-06-01T00:00:00+00:00",
  "removed_at": null,
  "is_active": true,
  "user": {
    "id": "uuid",
    "username": "jdoe",
    "full_name": "John Doe"
  }
}
```

### Formato de errores

Todos los errores siguen el mismo formato:

```json
{
  "error": {
    "code": "CANNOT_REMOVE_LAST_ADMIN",
    "message": "Descripción legible del error"
  }
}
```

---

## 5. RBAC — Tabla de permisos

| Acción | `viewer` | `editor` | `owner` | `admin` (sistema) |
|---|:---:|:---:|:---:|:---:|
| Ver proyectos propios | ✓ | ✓ | ✓ | ✓ |
| Crear proyecto | ✗ | ✓ | ✓ | ✓ |
| Editar proyecto | ✗ | ✗ | ✓ | ✓ |
| Eliminar proyecto | ✗ | ✗ | ✓ | ✓ |
| Ver miembros | ✓ | ✓ | ✓ | ✓ |
| Agregar miembro | ✗ | ✓ | ✓ | ✓ |
| Asignar rol `owner` | ✗ | ✗ | ✓ | ✓ |
| Remover miembro | ✗ | ✓ | ✓ | ✓ |
| Ver historial membresías | ✗ | ✓ | ✓ | ✓ |
| Transferir ownership | ✗ | ✗ | ✓ | ✗ |
| Panel admin usuarios | ✗ | ✗ | ✗ | ✓ |
| Cambiar rol de usuario | ✗ | ✗ | ✗ | ✓ |

> **Nota:** El rol `admin` a nivel sistema (`users.role`) da acceso a cualquier proyecto aunque no sea miembro explícito. El rol `owner` en `project_members` es el rol dentro de un proyecto específico.

---

## 6. Audit logs

La tabla `audit_logs` registra acciones críticas del sistema. Acciones registradas en Sprint 2:

| Acción | Origen | Metadata |
|---|---|---|
| `role_changed` | `admin.py` | `{ user_id, new_role, previous_role }` |
| `project_deleted` | `project_service.py` | `{ project_name }` |
| `member_added` | `project_service.py` | `{ added_user_id, role }` |
| `member_removed` | `project_service.py` | `{ removed_user_id, previous_role }` |
| `ownership_transferred` | `project_service.py` | `{ previous_owner_id, new_owner_id, project_name }` |
| `password_change` | `auth_service.py` | — |
| `login` | `auth_service.py` | `{ ip_address }` |
| `logout` | `auth_service.py` | — |
| `register` | `auth_service.py` | — |
| `email_verified` | `auth_service.py` | — |

Schema de la tabla:

```sql
audit_logs(
  id          UUID PRIMARY KEY,
  user_id     UUID REFERENCES users(id),
  action      VARCHAR NOT NULL,
  entity_type VARCHAR,          -- "project" | "user" | etc.
  entity_id   UUID,
  metadata    JSONB,
  ip_address  VARCHAR,
  created_at  TIMESTAMPTZ DEFAULT now()
)
```

---

## 7. Ejecutar tests

```bash
cd backend

# Suite completa con cobertura
pytest tests/integration/ --cov=app --cov-report=term-missing -v

# Solo E01 auth
pytest tests/integration/test_auth.py -v

# Solo paginación y password service
pytest tests/integration/test_pagination_and_password.py -v

# Solo RBAC y proyectos
pytest tests/integration/test_rbac_and_projects.py -v
pytest tests/integration/test_rbac_and_projects_v2.py -v
```

### Estado de la suite

| Archivo | Tests | Cobertura |
|---|---|---|
| `test_auth.py` | 32 | Auth E01 |
| `test_health.py` | 2 | Health check |
| `test_pagination_and_password.py` | 14 | Paginación + password service |
| `test_rbac_and_projects.py` | ~38 | RBAC E02 + proyectos E03 |
| `test_rbac_and_projects_v2.py` | ~36 | RBAC E02 extendido |
| **Total** | **122** | **70%+** |

### CI pipeline

El pipeline corre en cada PR a `staging`:

```
ruff check → ruff format → mypy → pytest (cobertura mín. 70%)
```

---

## 8. Deuda técnica documentada

### ADR-01 — Sin rotación de refresh token (vigente)

**Decisión:** Los refresh tokens no rotan en cada uso en el MVP. Un solo token de larga duración (30 días) por sesión.

**Riesgo:** Si un refresh token es robado, el atacante tiene acceso hasta que expire o sea revocado manualmente.

**Plan post-MVP:** Implementar rotación con Redis para invalidación inmediata en escenarios multi-tab.

---

### DT-01 — Race condition multi-tab en bootstrap (Sprint 1)

Múltiples tabs abiertos simultáneamente pueden intentar refrescar el token en paralelo. ADR-01 lo mitiga para el MVP pero no lo elimina.

**Plan post-MVP:** Redis como store centralizado de refresh tokens con TTL.

---

### DT-02 — `password_service.py` no usado por el endpoint (Sprint 2)

El archivo `app/services/password_service.py` implementa un flujo alternativo de reset de contraseña. El endpoint `/auth/reset-password` usa `AuthService.reset_password()` en su lugar.

**Acción:** Eliminar `password_service.py` o migrar el endpoint en Sprint 3 antes de que genere confusión.

---

### DT-03 — `app/schemas/project.py` no usado (Sprint 2)

El archivo `app/schemas/project.py` define schemas Pydantic para proyectos que no se usan — los endpoints de `projects.py` usan schemas inline.

**Acción:** Eliminar en Sprint 3 o consolidar los schemas inline en este archivo.

---

### DT-04 — `app/dependencies.py` legacy no usado (Sprint 2)

El archivo `app/dependencies.py` es un módulo legacy del Sprint 1 reemplazado por `app/api/deps/`. No tiene cobertura de tests y está excluido del reporte de cobertura.

**Acción:** Eliminar en Sprint 3 tras confirmar que ningún módulo lo importa.

---

### DT-05 — `GET /tasks` con filtro por rol pendiente (E02)

El endpoint `GET /tasks` con filtro `assigned_to=me` para viewers (R-0203) no fue implementado en Sprint 2 porque depende de E04 (gestión de tareas — Sprint 3).

**Plan:** Implementar en Sprint 3 junto con los endpoints de tareas.

---

### DT-06 — Invitación de miembros por email pendiente (E03)

La funcionalidad de invitar miembros al proyecto via email (R-0308) fue descartada del Sprint 2. Actualmente solo se pueden agregar miembros conociendo el `user_id`.

**Plan:** Implementar en Sprint 4 junto con el sistema de notificaciones.

---

*Última actualización: Sprint 2 · Kanban MVP PRD v2*