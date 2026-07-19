"""Application factory for SAVE-US."""

import os

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the SAVE-US Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "save-us-dev-only-secret"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import routes

    app.register_blueprint(routes.bp)
    return app
