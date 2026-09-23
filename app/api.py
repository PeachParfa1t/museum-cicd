import sqlite3

from flask import Blueprint, jsonify, request

from .db import get_db


api_bp = Blueprint("api", __name__, url_prefix="/api")


RESOURCE_CONFIG = {
    "collections": {
        "fields": ("name", "theme", "founded_year", "description"),
        "required": ("name", "theme"),
        "integers": ("founded_year",),
    },
    "halls": {
        "fields": ("name", "floor", "capacity", "description"),
        "required": ("name", "floor", "capacity"),
        "integers": ("floor", "capacity"),
    },
    "employees": {
        "fields": ("full_name", "position", "email", "phone"),
        "required": ("full_name", "position", "email"),
        "integers": (),
    },
    "events": {
        "fields": ("title", "event_date", "location", "description"),
        "required": ("title", "event_date", "location"),
        "integers": (),
    },
    "exhibits": {
        "fields": (
            "inventory_number",
            "title",
            "creation_year",
            "material",
            "collection_id",
            "hall_id",
        ),
        "required": ("inventory_number", "title", "material"),
        "integers": ("creation_year", "collection_id", "hall_id"),
    },
}


def resource_or_404(resource):
    config = RESOURCE_CONFIG.get(resource)
    if config is None:
        return None, (jsonify({"error": "Неизвестный раздел музея."}), 404)
    return config, None


def serialize_row(row):
    return dict(row) if row is not None else None


def validate_payload(config, partial=False):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, "Тело запроса должно содержать JSON-объект."

    clean = {}
    for field in config["fields"]:
        if field not in data:
            continue

        value = data[field]
        if isinstance(value, str):
            value = value.strip()

        if value == "" and field in config["integers"]:
            value = None

        if value is not None and field in config["integers"]:
            try:
                value = int(value)
            except (TypeError, ValueError):
                return None, f"Поле {field} должно быть целым числом."

        clean[field] = value

    missing = [
        field
        for field in config["required"]
        if (not partial and field not in clean)
        or (field in clean and clean[field] in (None, ""))
    ]
    if missing:
        return None, "Не заполнены обязательные поля: " + ", ".join(missing)

    if partial and not clean:
        return None, "Не передано ни одного изменяемого поля."

    return clean, None


def select_query(resource, single=False):
    where = " WHERE e.id = ?" if single else ""
    order = "" if single else " ORDER BY e.id DESC"
    if resource == "exhibits":
        return (
            "SELECT e.*, c.name AS collection_name, h.name AS hall_name "
            "FROM exhibits e "
            "LEFT JOIN collections c ON c.id = e.collection_id "
            "LEFT JOIN halls h ON h.id = e.hall_id"
            + where
            + order
        )

    alias = resource[0]
    where = f" WHERE {alias}.id = ?" if single else ""
    order = "" if single else f" ORDER BY {alias}.id DESC"
    return f"SELECT {alias}.* FROM {resource} {alias}{where}{order}"


@api_bp.get("/stats")
def stats():
    database = get_db()
    counts = {}
    for resource in RESOURCE_CONFIG:
        counts[resource] = database.execute(
            f"SELECT COUNT(*) AS total FROM {resource}"
        ).fetchone()["total"]
    return jsonify(counts)


@api_bp.get("/<resource>")
def list_records(resource):
    _config, error = resource_or_404(resource)
    if error:
        return error

    rows = get_db().execute(select_query(resource)).fetchall()
    return jsonify([serialize_row(row) for row in rows])


@api_bp.post("/<resource>")
def create_record(resource):
    config, error = resource_or_404(resource)
    if error:
        return error

    data, validation_error = validate_payload(config)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    fields = list(data)
    placeholders = ", ".join("?" for _field in fields)
    query = (
        f"INSERT INTO {resource} ({', '.join(fields)}) "
        f"VALUES ({placeholders})"
    )

    database = get_db()
    try:
        cursor = database.execute(query, [data[field] for field in fields])
        database.commit()
    except sqlite3.IntegrityError as exc:
        return jsonify({"error": f"Не удалось сохранить запись: {exc}"}), 409

    row = database.execute(select_query(resource, single=True), (cursor.lastrowid,)).fetchone()
    return jsonify(serialize_row(row)), 201


@api_bp.get("/<resource>/<int:record_id>")
def get_record(resource, record_id):
    _config, error = resource_or_404(resource)
    if error:
        return error

    row = get_db().execute(select_query(resource, single=True), (record_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Запись не найдена."}), 404
    return jsonify(serialize_row(row))


@api_bp.put("/<resource>/<int:record_id>")
def update_record(resource, record_id):
    config, error = resource_or_404(resource)
    if error:
        return error

    database = get_db()
    exists = database.execute(
        f"SELECT id FROM {resource} WHERE id = ?", (record_id,)
    ).fetchone()
    if exists is None:
        return jsonify({"error": "Запись не найдена."}), 404

    data, validation_error = validate_payload(config, partial=True)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    assignments = ", ".join(f"{field} = ?" for field in data)
    values = [data[field] for field in data] + [record_id]
    try:
        database.execute(
            f"UPDATE {resource} SET {assignments} WHERE id = ?", values
        )
        database.commit()
    except sqlite3.IntegrityError as exc:
        return jsonify({"error": f"Не удалось изменить запись: {exc}"}), 409

    row = database.execute(select_query(resource, single=True), (record_id,)).fetchone()
    return jsonify(serialize_row(row))


@api_bp.delete("/<resource>/<int:record_id>")
def delete_record(resource, record_id):
    _config, error = resource_or_404(resource)
    if error:
        return error

    database = get_db()
    cursor = database.execute(
        f"DELETE FROM {resource} WHERE id = ?", (record_id,)
    )
    database.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Запись не найдена."}), 404
    return "", 204
