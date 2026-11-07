import pytest

from app import create_app, store
from notification_service import clear_notifications


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    store.reset()
    clear_notifications()
    with app.test_client() as client:
        yield client
    store.reset()
    clear_notifications()
