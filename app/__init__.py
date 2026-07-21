"""Application factory for SAVE-US."""

import os

import click
from dotenv import load_dotenv
from flask import Flask

from .extensions import db, migrate


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the SAVE-US Flask application."""
    # Local `.env` values make the documented demo setup work, while host-level
    # variables always take precedence in deployment environments. Test
    # configurations remain isolated from a developer's local credentials.
    if test_config is None:
        load_dotenv(override=False)
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "save-us-dev-only-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(app.instance_path, 'save_us.sqlite3')}",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_PHOTO_UPLOAD_BYTES=5 * 1024 * 1024,
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY"),
        OPENAI_MODEL=os.environ.get("OPENAI_MODEL", "gpt-5.6"),
        OPENAI_MEDIA_MODEL=os.environ.get("OPENAI_MEDIA_MODEL", os.environ.get("OPENAI_MODEL", "gpt-5.6")),
        OPENAI_TIMEOUT_SECONDS=20,
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register SQLAlchemy models before migrations inspect db.metadata.
    from . import models, routes  # noqa: F401

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all tables defined by the current SQLAlchemy metadata."""
        db.create_all()
        click.echo(f"Database ready: {app.config['SQLALCHEMY_DATABASE_URI']}")

    @app.cli.command("seed-demo")
    def seed_demo_command() -> None:
        """Create idempotent CEMAC demo users, preferences, and safe scenarios."""
        from .seed import seed_demo_data

        users_created, preferences_created = seed_demo_data()
        click.echo(
            "Demo data ready: "
            f"{users_created} user(s) and {preferences_created} preference set(s) created; "
            "safe alert, moderation, administration, and notification scenarios are available."
        )

    app.register_blueprint(routes.bp)
    return app
