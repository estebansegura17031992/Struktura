# Integración E04 — alcance completo (PM confirmó: todo en un solo PR)

## 1. Archivos a copiar/sobreescribir en tu repo

| Archivo | Ruta real | Estado |
|---|---|---|
| Migración correctiva del seed | `backend/app/db/migrations/versions/0003_fix_max_task_assignees_seed.py` | ya copiado |
| DTOs (incluye `TaskAssigneesUpdate` nuevo) | `backend/app/schemas/task.py` | **sobreescribir** — se agregó el schema de assignees |
| Repository (filtros, FTS, timer ADR-03) | `backend/app/repositories/task_repository.py` | **sobreescribir** |
| Service (list_tasks, update_assignees, audit log en status) | `backend/app/services/task_service.py` | **sobreescribir** |
| Router (GET + PATCH /assignees nuevos) | `backend/app/api/v1/endpoints/tasks.py` | **sobreescribir** |
| Tests de integración | `backend/tests/integration/test_e04_tasks.py` | nuevo |
| `router.py` | `backend/app/api/v1/router.py` | ya registrado |

## 2. Qué se agregó sobre lo que ya tenías corriendo

- **`GET /tasks`** — filtros (`priority`, `status`, `assigned_to`, `due_date_from/to`, `search`), paginación clamp a 50 (R-0405), FTS vía `search_vector` + GIN (R-0404, mínimo 2 caracteres, error 422 si es menor).
- **`PATCH /tasks/{id}/assignees`** — reemplaza el set de asignados, valida `max_task_assignees`, e implementa ADR-03: al pasar de 1 a 2+ asignados con timer activo, lo detiene automáticamente (`stop_reason='multi_assignee'`) y registra `audit_logs` con `action='timer_stopped_multi_assignee'`. Al bajar a 1, `timer_disabled` vuelve a `false`.
- **`PATCH /tasks/{id}/status`** corregido — ahora registra `audit_logs` con `action='task_status_change'` (R-0409, se me había pasado en la primera pasada) y el permiso se amplía: editor/owner siempre puede; un asignado con rol viewer **nunca** puede, ni siquiera estando asignado (regla explícita del PM).

## 3. Dependencia con E05 (cronómetro) — importante para el PR

`PATCH /tasks/{id}/assignees` necesita leer/detener un timer activo (ADR-03), pero **`app/api/v1/endpoints/timers.py` no existe todavía** (es Sprint 4/E05). Por eso:
- `task_repository.py` tiene 2 métodos mínimos (`get_active_timer`, `stop_timer`) que operan directo sobre `TaskTimeEntry` — sin repository/service de timers dedicado.
- Cuando el equipo construya E05, hay que decidir si esos 2 métodos se migran a un `timer_repository.py` compartido, o si se dejan donde están y el timer_service de E05 los reutiliza. Vale la pena dejarlo como punto de discusión en el PR, no decidirlo unilateralmente acá.

## 4. Aplicar y probar

```powershell
cd backend
alembic upgrade head
alembic current   # 0003 (head)
```

```powershell
pytest tests/integration/test_e04_tasks.py -v
```

Si algún test de ADR-03 falla, lo más probable es un desfase entre el nombre de columna `stop_reason` asumido y el real — confirmar contra `app/models/task.py::TaskTimeEntry` antes de reportar bug.

## 5. Commit

```powershell
git add backend/app/db/migrations/versions/0003_fix_max_task_assignees_seed.py `
        backend/app/schemas/task.py `
        backend/app/repositories/task_repository.py `
        backend/app/services/task_service.py `
        backend/app/api/v1/endpoints/tasks.py `
        backend/app/api/v1/router.py `
        backend/app/api/v1/tasks.py `
        backend/tests/integration/test_e04_tasks.py `
        backend/app/docs/openapi_tasks_contract_dia2.json `
        backend/app/docs/README_integracion_E04.md

git status
git commit -m "feat(E04): CRUD completo de tasks - migracion, DTOs, filtros/FTS, ADR-03, RBAC heredado, tests"
git push origin sp3_backend_task
```

## 6. Nota para Security (sigue vigente)

`app/api/v1/endpoints/tasks.py` no reimplementa `require_role()`/`verify_project_membership()` de `app/dependencies.py` (no está wireado a ningún router real). Sigue el patrón real de `get_project_member` de `projects.py`. A diferencia de `projects.py`, aquí no hay permisos inline — todo vive en dependencias (`require_task_role`, `require_task_status_permission`).