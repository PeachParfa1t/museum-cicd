import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db():
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def ensure_database(seed=True):
    database = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    database.executescript(schema_path.read_text(encoding="utf-8"))

    if seed:
        seed_path = Path(__file__).with_name("seed.sql")
        database.executescript(seed_path.read_text(encoding="utf-8"))

    database.commit()


@click.command("init-db")
def init_db_command():
    """Create missing tables and add demonstration records."""
    ensure_database(seed=True)
    click.echo("База данных музея подготовлена.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
