"""Create the local SAVE-US database from the current SQLAlchemy metadata."""

import sys
from pathlib import Path

# Allow direct execution with ".venv/bin/python scripts/init_db.py".
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db


app = create_app()

with app.app_context():
    db.create_all()
    print(f"Database ready: {app.config['SQLALCHEMY_DATABASE_URI']}")
