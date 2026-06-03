"""
Base declarativa de SQLAlchemy.
IMPORTANTE: este archivo SOLO declara Base.
Las importaciones de modelos van en app/db/registry.py para evitar
importaciones circulares (user.py importa Base, base.py importaba user.py).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
