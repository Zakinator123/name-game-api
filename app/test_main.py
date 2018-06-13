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
    assert b'True' in response.data

def test_db_connected(client):
    response = client.get('/test_db_connection')
    assert b'[]' in response.data