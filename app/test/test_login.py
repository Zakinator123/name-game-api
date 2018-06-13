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


def test_login(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    # TODO: Figure out how to use bcrypt here so that I don't have to use the signup endpoint while testing the login endpoint
    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': username, 'password': password})
    assert ('token' in (response.get_json()) and response.get_json()['status'] == 'Success')

def test_repeated_login(client):

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    # TODO: Figure out how to use bcrypt here so that I don't have to use the signup endpoint while testing the login endpoint
    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': username, 'password': password})
    response = client.post('/login', json={'username': username, 'password': password})

    assert ('token' in (response.get_json()) and response.get_json()['status'] == 'Success')



def test_invalid_username_login(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': 'BOGUS USERNAME', 'password': password})
    assert (response.get_json()['status'] == 'Error' and response.get_json()['message'] == "User does not exist.")



def test_invalid_password_login(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})

    response = client.post('/login', json={'username': username, 'password': 'BOGUS PASSWORD'})
    assert (response.get_json()['status'] == 'Error' and response.get_json()['message'] == "Incorrect password.")


def test_missing_credentials(client):
    response = client.post('/login', json={'useless_input': 'BOGUS'})
    assert (response.get_json()['status'] == 'Error' and response.get_json()['message'] == "Appropriate login credentials were not provided.")

