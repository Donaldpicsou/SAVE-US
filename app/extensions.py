"""Shared Flask extensions for SAVE-US."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


# Models are added in T4. Keeping the extension instances here prevents
# circular imports and gives Flask-Migrate one shared metadata registry.
db = SQLAlchemy()
migrate = Migrate()
