import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": tmp_path / "test.db",
            "SEED_DATABASE": False,
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
