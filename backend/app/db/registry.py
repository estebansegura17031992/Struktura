"""
Importa todos los modelos para que Alembic los detecte en autogenerate.
Este archivo se importa SOLO desde migrations/env.py, nunca desde los modelos.
Así se evita la importación circular:
  user.py → base.py → user.py  (circular ❌)
  user.py → base.py            (ok ✓)
  env.py  → registry.py → todos los modelos (ok ✓)
"""
from app.models.user import User, EmailVerificationToken, RefreshToken, PasswordResetToken  # noqa: F401
from app.models.auth import SystemSetting  # noqa: F401
from app.models.project import Project, ProjectMember, ProjectInvitation  # noqa: F401
from app.models.task import Task, TaskAssignee, TaskTimeEntry, TaskComment, CommentMention  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
