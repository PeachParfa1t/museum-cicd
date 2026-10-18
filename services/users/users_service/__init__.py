import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("USERS_DATABASE_PATH", "/data/users.db"),
        INIT_DATABASE=os.environ.get("INIT_DATABASE", "1") == "1",
    )
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "users_db" not in g:
            path = Path(app.config["DATABASE"])
            path.parent.mkdir(parents=True, exist_ok=True)
            g.users_db = sqlite3.connect(path, timeout=30)
            g.users_db.row_factory = sqlite3.Row
        return g.users_db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("users_db", None)
        if db is not None:
            db.close()

    if app.config["INIT_DATABASE"]:
        with app.app_context():
            get_db().execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "full_name TEXT NOT NULL, "
                "email TEXT NOT NULL UNIQUE, "
                "phone TEXT NOT NULL DEFAULT ''"
                ")"
            )
            get_db().commit()

    def payload(partial=False):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, "Тело запроса должно содержать JSON-объект."
        clean = {}
        for key in ("full_name", "email", "phone"):
            if key in data:
                if not isinstance(data[key], str):
                    return None, f"Поле {key} должно быть строкой."
                clean[key] = data[key].strip()
        if not partial and "phone" not in clean:
            clean["phone"] = ""
        for key in ("full_name", "email"):
            if (not partial or key in clean) and not clean.get(key):
                return None, f"Не заполнено обязательное поле: {key}."
        if "email" in clean and ("@" not in clean["email"] or " " in clean["email"]):
            return None, "Некорректная электронная почта."
        if partial and not clean:
            return None, "Не передано ни одного изменяемого поля."
        return clean, None

    def one(user_id):
        row = get_db().execute(
            "SELECT id, full_name, email, phone FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return jsonify({"service": "users", "status": "ok"})

    @app.get("/api/users")
    def list_users():
        rows = get_db().execute(
            "SELECT id, full_name, email, phone FROM users ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/users")
    def create_user():
        data, error = payload()
        if error:
            return jsonify({"error": error}), 400
        db = get_db()
        try:
            cursor = db.execute(
                "INSERT INTO users (full_name, email, phone) VALUES (?, ?, ?)",
                (data["full_name"], data["email"], data["phone"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Такая почта уже зарегистрирована."}), 409
        return jsonify(one(cursor.lastrowid)), 201

    @app.get("/api/users/<int:user_id>")
    def get_user(user_id):
        user = one(user_id)
        return jsonify(user) if user else (jsonify({"error": "Пользователь не найден."}), 404)

    @app.put("/api/users/<int:user_id>")
    def update_user(user_id):
        if not one(user_id):
            return jsonify({"error": "Пользователь не найден."}), 404
        data, error = payload(partial=True)
        if error:
            return jsonify({"error": error}), 400
        fields = ", ".join(f"{key} = ?" for key in data)
        db = get_db()
        try:
            db.execute(
                f"UPDATE users SET {fields} WHERE id = ?",
                [*data.values(), user_id],
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Такая почта уже зарегистрирована."}), 409
        return jsonify(one(user_id))

    @app.delete("/api/users/<int:user_id>")
    def delete_user(user_id):
        db = get_db()
        cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Пользователь не найден."}), 404
        return "", 204

    return app
