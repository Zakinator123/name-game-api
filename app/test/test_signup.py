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


def test_signup(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'], os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM user")
    db.commit()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    sql = "SELECT * FROM user WHERE username=%s"
    cursor.execute(sql, (username, ))
    db.close()
    assert cursor.rowcount > 0


def test_duplicate_username_signup(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/signup', json={'username': username, 'password': password})
    assert (response.get_json()['message'] == "Username already taken.")


def test_missing_credentials_signup(client):
    response = client.post('/signup', json={'bogus key': 'bogus value'})

    assert (response.get_json()['message'] == "Appropriate signup credentials were not provided.")
