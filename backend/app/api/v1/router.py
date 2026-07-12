"""
Router principal de la API v1.
Agrega todos los sub-routers de cada dominio.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (  # Sprint 2 + E04
    admin,
    auth,
    health,
    projects,
    tasks,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)  # Sprint 2 — E02
api_router.include_router(projects.router)  # Sprint 2 — E03

# Sprint 3+:
# from app.api.v1.endpoints import tasks, timer, dashboard, comments
# api_router.include_router(tasks.router)
