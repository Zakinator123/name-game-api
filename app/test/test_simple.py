import os
import pytest
from main import app
import MySQLdb
import MySQLdb.cursors


@pytest.fixture
def client(request):
    test_client = app.test_client()
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("TRUNCATE TABLE authenticator")
    db.commit()
    db.close()

    def teardown():
        pass

    request.addfinalizer(teardown)
    return test_client


def test_home(client):
    response = client.get('/')
    assert b'Welcome to the Name Game API!' in response.data


def test_db_connected(client):
    response = client.get('/test_db_connection')
    table_count = int(response.get_json()['table_count'])
    assert table_count > 0

