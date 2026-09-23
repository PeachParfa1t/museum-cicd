import pytest


RESOURCE_CASES = [
    (
        "collections",
        {
            "name": "Археология",
            "theme": "Древняя история",
            "founded_year": 1995,
            "description": "Археологические находки региона.",
        },
        {"name": "Археология и этнография"},
    ),
    (
        "halls",
        {
            "name": "Зал древностей",
            "floor": 1,
            "capacity": 35,
            "description": "Постоянная экспозиция.",
        },
        {"capacity": 40},
    ),
    (
        "employees",
        {
            "full_name": "Мария Орлова",
            "position": "Научный сотрудник",
            "email": "orlova@example.test",
            "phone": "+7 900 000-00-01",
        },
        {"position": "Старший научный сотрудник"},
    ),
    (
        "events",
        {
            "title": "Открытие выставки",
            "event_date": "2026-11-20",
            "location": "Главный зал",
            "description": "Встреча с куратором.",
        },
        {"location": "Лекционный зал"},
    ),
]


def test_homepage_and_healthcheck(client):
    homepage = client.get("/")
    assert homepage.status_code == 200
    assert "Музейный архив" in homepage.get_data(as_text=True)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "ok"


@pytest.mark.parametrize("resource,payload,changes", RESOURCE_CASES)
def test_crud_cycle_for_regular_resources(client, resource, payload, changes):
    created = client.post(f"/api/{resource}", json=payload)
    assert created.status_code == 201
    record_id = created.get_json()["id"]

    listed = client.get(f"/api/{resource}")
    assert listed.status_code == 200
    assert len(listed.get_json()) == 1

    fetched = client.get(f"/api/{resource}/{record_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["id"] == record_id

    updated = client.put(f"/api/{resource}/{record_id}", json=changes)
    assert updated.status_code == 200
    for key, value in changes.items():
        assert updated.get_json()[key] == value

    deleted = client.delete(f"/api/{resource}/{record_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/{resource}/{record_id}").status_code == 404


def test_crud_cycle_for_exhibits_with_relations(client):
    collection = client.post(
        "/api/collections",
        json={"name": "Живопись", "theme": "Искусство", "founded_year": 2001},
    ).get_json()
    hall = client.post(
        "/api/halls",
        json={"name": "Картинная галерея", "floor": 2, "capacity": 50},
    ).get_json()

    payload = {
        "inventory_number": "Ж-100",
        "title": "Утро у реки",
        "creation_year": 1912,
        "material": "Холст, масло",
        "collection_id": collection["id"],
        "hall_id": hall["id"],
    }
    created = client.post("/api/exhibits", json=payload)
    assert created.status_code == 201
    exhibit = created.get_json()
    assert exhibit["collection_name"] == "Живопись"
    assert exhibit["hall_name"] == "Картинная галерея"

    fetched = client.get(f"/api/exhibits/{exhibit['id']}")
    assert fetched.status_code == 200

    updated = client.put(
        f"/api/exhibits/{exhibit['id']}", json={"material": "Картон, масло"}
    )
    assert updated.status_code == 200
    assert updated.get_json()["material"] == "Картон, масло"

    deleted = client.delete(f"/api/exhibits/{exhibit['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/exhibits").get_json() == []


def test_validation_and_unknown_resource(client):
    response = client.post("/api/collections", json={"name": "Без темы"})
    assert response.status_code == 400
    assert "обязательные поля" in response.get_json()["error"]

    created = client.post(
        "/api/collections", json={"name": "Фонд", "theme": "История"}
    ).get_json()
    invalid_update = client.put(
        f"/api/collections/{created['id']}", json={"name": ""}
    )
    assert invalid_update.status_code == 400

    assert client.get("/api/unknown").status_code == 404


def test_statistics(client):
    client.post(
        "/api/events",
        json={"title": "Лекция", "event_date": "2026-12-01", "location": "Музей"},
    )
    stats = client.get("/api/stats")
    assert stats.status_code == 200
    assert stats.get_json()["events"] == 1
    assert set(stats.get_json()) == {
        "collections",
        "employees",
        "events",
        "exhibits",
        "halls",
    }
