import pytest

from publishers import app


@pytest.fixture(name="app")
def fixture_app():
    app.testing = True
    yield app
    app.testing = False


@pytest.fixture
def client(app):
    return app.test_client()
