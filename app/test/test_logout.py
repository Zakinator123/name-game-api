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
        db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'], os.environ['RDS_DB_NAME'])
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("TRUNCATE TABLE authenticator")
        db.commit()
        cursor.execute("DELETE FROM user")
        db.commit()
        db.close()

    request.addfinalizer(teardown)
    return test_client


def test_logout(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': username, 'password': password})

    token = response.get_json()['token']

    response = client.post('/logout', json={'token': token})
    assert (response.get_json()['status'] == 'Success' and response.get_json()['message'] == 'Successfully logged out.')


def test_logout_missing_authenticator(client):
    response = client.post('/logout', json={'bogus_data': 'bogus data'})
    assert (response.get_json()['status'] == 'Error')


def test_logout_invalid_authenticator(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': username, 'password': password})

    token = response.get_json()['token'] + 'token corruption string'

    response = client.post('/logout', json={'token': token})
    assert (response.get_json()['status'] == 'Error')

