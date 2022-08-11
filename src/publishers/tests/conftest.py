import pytest
from publishers.__init__ import create_app


@pytest.fixture()
def app():
    yield create_app("tests/.env")


@pytest.fixture
def client(app):
    app.config.update(
        {
            "API_KEY": "test_key",
        }
    )

    return app.test_client()
