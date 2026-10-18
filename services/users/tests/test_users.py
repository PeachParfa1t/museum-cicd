from users_service import create_app


def test_users_crud_and_own_database(tmp_path):
    database = tmp_path / "users.db"
    client = create_app({"TESTING": True, "DATABASE": database}).test_client()

    assert client.get("/health").get_json() == {"service": "users", "status": "ok"}
    created = client.post(
        "/api/users",
        json={"full_name": "Анна Иванова", "email": "anna@example.test"},
    )
    assert created.status_code == 201
    user_id = created.get_json()["id"]
    assert database.exists()

    assert client.post(
        "/api/users",
        json={"full_name": "Дубликат", "email": "anna@example.test"},
    ).status_code == 409
    assert client.get("/api/users").get_json()[0]["id"] == user_id
    assert client.put(
        f"/api/users/{user_id}", json={"phone": "+7 900 000-00-00"}
    ).get_json()["phone"] == "+7 900 000-00-00"
    assert client.delete(f"/api/users/{user_id}").status_code == 204
    assert client.get(f"/api/users/{user_id}").status_code == 404


def test_users_validation(tmp_path):
    client = create_app({"TESTING": True, "DATABASE": tmp_path / "users.db"}).test_client()
    assert client.post("/api/users", json={"full_name": "Тест"}).status_code == 400
    assert client.post(
        "/api/users", json={"full_name": "Тест", "email": "invalid"}
    ).status_code == 400


def test_users_persist_across_app_restarts(tmp_path):
    database = tmp_path / "users.db"
    first = create_app({"TESTING": True, "DATABASE": database}).test_client()
    assert first.post(
        "/api/users", json={"full_name": "Гость", "email": "guest@example.test"}
    ).status_code == 201

    second = create_app({"TESTING": True, "DATABASE": database}).test_client()
    assert [user["full_name"] for user in second.get("/api/users").get_json()] == ["Гость"]
