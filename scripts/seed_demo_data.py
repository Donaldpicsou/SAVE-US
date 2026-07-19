"""Seed the SAVE-US local database with CEMAC demo users."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.seed import seed_demo_data


app = create_app()

with app.app_context():
    users_created, preferences_created = seed_demo_data()
    print(
        "Demo data ready: "
        f"{users_created} user(s) and {preferences_created} preference set(s) created."
    )
