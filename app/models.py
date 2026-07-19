"""SQLAlchemy model registry.

Business models (User, AlertPreference, Alert, and related entities) are
introduced in roadmap task T4. Import this module from the app factory so
Alembic discovers every model as the registry grows.
"""

from .extensions import db

__all__ = ["db"]
