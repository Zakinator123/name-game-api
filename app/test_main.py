import json
import pytest
from main import app

@pytest.fixture
def client(request):
    test_client = app.test_client()

    def teardown():
        pass

    request.addfinalizer(teardown)
    return test_client


def test_home(client):
    response = client.get('/')
    assert b'Welcome to the Name Game API!' in response.data