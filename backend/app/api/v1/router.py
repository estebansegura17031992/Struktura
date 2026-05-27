"""
Router principal de la API v1.
Agrega todos los sub-routers de cada dominio.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)

# Sprint 2+ — se agregan aquí:
# from app.api.v1.endpoints import projects, tasks, timer, dashboard, comments
# api_router.include_router(projects.router)
# api_router.include_router(tasks.router)
