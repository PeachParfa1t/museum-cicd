import os

from flask import Flask, jsonify, render_template

from . import db
from .api import api_bp


def create_app(test_config=None):
    """Create and configure the museum application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "DATABASE_PATH", os.path.join(app.instance_path, "museum.db")
        ),
        SEED_DATABASE=True,
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.ensure_database(seed=app.config["SEED_DATABASE"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        database = db.get_db()
        database.execute("SELECT 1").fetchone()
        return jsonify({"status": "ok", "service": "museum-archive"})

    return app
