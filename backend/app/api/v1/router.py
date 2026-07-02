"""
Router principal de la API v1.
Agrega todos los sub-routers de cada dominio.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, health, projects, tasks, users  # Sprint 2 + E04

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)  # Sprint 2 - E02
api_router.include_router(projects.router)  # Sprint 2 - E03
api_router.include_router(tasks.router)  # E04
