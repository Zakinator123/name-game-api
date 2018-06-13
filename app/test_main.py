import json
import os
import pytest
from main import app
import MySQLdb
import MySQLdb.cursors

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


def test_db_connected(client):
    response = client.get('/test_db_connection')
    table_count = int(response.get_json()['table_count'])
    assert table_count > 0


def test_signup(client):
    db = MySQLdb.connect(os.environ['TESTDB_HOSTNAME'], os.environ['TESTDB_USERNAME'], os.environ['TESTDB_PASSWORD'], os.environ['TESTDB_DBNAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("TRUNCATE TABLE user")
    db.commit()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    sql = "SELECT * FROM user WHERE username=%s"
    cursor.execute(sql, (username, ))
    assert cursor.rowcount > 0


def test_duplicate_username_signup(client):
    db = MySQLdb.connect(os.environ['TESTDB_HOSTNAME'], os.environ['TESTDB_USERNAME'], os.environ['TESTDB_PASSWORD'],
                         os.environ['TESTDB_DBNAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("TRUNCATE TABLE user")
    db.commit()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/signup', json={'username': username, 'password': password})
    assert (response.get_json()['message'] == "Username already taken.")


def test_missing_credentials_signup(client):
    response = client.post('/signup', json={'bogus key': 'bogus value'})

    assert (response.get_json()['message'] == "Appropriate signup credentials were not provided.")
