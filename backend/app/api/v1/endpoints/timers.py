"""Endpoint de cronómetro sin scope de tarea — E05 · Sprint 4 · Objetivo 2.

GET /timers/active — el timer activo del usuario actual, si existe. Vive
en su propio router (no bajo /tasks) porque no depende de un task_id en
la URL: el frontend lo usa para saber, al recargar la página o cambiar de
dispositivo, si hay un cronómetro corriendo y en qué tarea.

Ubicación en el repo: backend/app/api/v1/endpoints/timers.py
"""

from fastapi import APIRouter

from app.api.deps.auth import DB, CurrentUser
from app.schemas.timer import ActiveTimerOut
from app.services.timer_service import TimerService

router = APIRouter(prefix="/timers", tags=["timers"])


@router.get("/active", response_model=ActiveTimerOut | None)
async def get_active_timer(current_user: CurrentUser, db: DB):
    """Retorna la entrada activa del usuario actual (o null), con el tiempo
    transcurrido calculado al momento de la consulta."""
    service = TimerService(db)
    return await service.get_active(user_id=current_user.id)
