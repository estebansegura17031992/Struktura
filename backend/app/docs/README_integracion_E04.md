# Integración E04 — rutas reales confirmadas en el repo

Todas las rutas de abajo fueron confirmadas contra el árbol real de
`Struktura/backend` (no son una convención asumida). Los modelos
(`app/models/task.py`) **no se tocan** — ya existen, completos, hechos por
otro compañero de equipo.

## 1. Registrar el router en `app/api/v1/router.py`

Tu `router.py` actual tiene esto comentado:

```python
# Sprint 3+:
# from app.api.v1.endpoints import tasks, timer, dashboard, comments
# api_router.include_router(tasks.router)
```

Descomentar solo la parte de `tasks`:

```python
from app.api.v1.endpoints import admin, auth, health, projects, tasks, users  # + tasks

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)  # nuevo — E04
```

## 2. Aplicar la migración 0003 (corrección de seed, NO crea tablas)

`0001_initial_schema.py` ya crea `tasks`, `task_assignees`, los ENUM,
`search_vector` y el índice GIN. La única pieza que faltaba y que corrige
esta migración es el valor de `system_settings.max_task_assignees`, que
`0001` insertó como `10` y el PM pidió `5`.

```powershell
cd backend
alembic upgrade head
alembic current   # debe mostrar 0003 (head)
```

Verificar:
```sql
SELECT key, value FROM system_settings WHERE key = 'max_task_assignees';
-- max_task_assignees | 5
```

## 3. Archivos entregados y su ruta real

| Día | Archivo | Ruta real en tu repo | Estado |
|---|---|---|---|
| 1 | Migración correctiva del seed | `backend/app/db/migrations/versions/0003_fix_max_task_assignees_seed.py` | nuevo |
| 1/2 | Modelo `Task`/`TaskAssignee` | `backend/app/models/task.py` | **ya existe — no tocar** |
| 2 | DTOs request/response | `backend/app/schemas/task.py` | nuevo |
| 2 | Contrato OpenAPI congelado | `backend/app/docs/openapi_tasks_contract_dia2.json` | confirmar si ya existe algo con este nombre antes de sobreescribir |
| 3 | Repository | `backend/app/repositories/task_repository.py` | nuevo |
| 3 | Service (reglas de negocio) | `backend/app/services/task_service.py` | nuevo |
| 3 | Router (CRUD + RBAC heredado) | `backend/app/api/v1/endpoints/tasks.py` | nuevo — **no** `app/api/v1/tasks.py` (ese archivo está vacío/sin usar) |
| — | Este README | `backend/app/docs/README_integracion_E04.md` | confirmar si ya existe contenido antes de sobreescribir |

Antes de copiar `openapi_tasks_contract_dia2.json` y este README, corre:
```powershell
Get-ChildItem backend\app\docs
```
En el árbol original ya vimos que `app/docs/` tiene archivos con nombres
truncados (`openapi_...`, `README_i...`) — puede que ya existan versiones
de otro compañero. Si es así, pega su contenido antes de sobreescribir,
igual que se hizo con `task.py`.

## 4. Nota para Security (Día 3)

`app/api/v1/endpoints/tasks.py` no reimplementa `require_role()` ni
`verify_project_membership()` de `app/dependencies.py` porque ese módulo
no está wireado a ningún router real. Sigue el patrón que sí está en
producción (`get_project_member` local de `projects.py`), adaptado para
resolver `project_id` desde una tarea existente. A diferencia de
`projects.py` (que tiene `if membership.role != "owner"...` inline en
`update_project`/`delete_project`), aquí el chequeo de rol vive en la
dependencia `require_task_role(...)` — sin lógica de permisos inline en
los endpoints, por pedido explícito del PM.

## 5. Diferencia de convención a decidir con el equipo (no bloqueante)

`projects.py` define sus DTOs (`ProjectCreateRequest`, `ProjectResponse`,
etc.) inline en el mismo archivo del router, no en `app/schemas/`.
El `task.py` de schemas que entregamos aquí sí vive en esa carpeta, que
es consistente con el resto de `app/schemas/` pero no con el estilo
inline de `projects.py`. No es bloqueante para Día 3, pero vale la pena
que el equipo unifique el criterio antes de Sprint 4.