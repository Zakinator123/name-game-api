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
    cursor.execute("DELETE FROM authenticator")
    db.commit()
    cursor.execute("DELETE FROM game_session")
    db.commit()
    db.close()

    def teardown():
        db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                             os.environ['RDS_DB_NAME'])
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("DELETE FROM authenticator")
        db.commit()
        cursor.execute("DELETE FROM game_session")
        db.commit()
        cursor.execute("DELETE FROM user")
        db.commit()
        db.close()

    request.addfinalizer(teardown)
    return test_client


def test_new_standard_game(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    cursor.execute("DELETE FROM game_session")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})
    response = client.post('/login', json={'username': username, 'password': password})
    token = response.get_json()['token']

    response = client.post('/game', json={'token': token, 'game_type': 'standard'})
    choice_list = response.get_json()['question']['choices']

    assert (response.get_json()['status'] == 'Success' and len(choice_list) == 6)


def test_game_answer(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    cursor.execute("DELETE FROM game_session")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})
    response = client.post('/login', json={'username': username, 'password': password})
    token = response.get_json()['token']

    response = client.post('/game', json={'token': token, 'game_type': 'standard'})
    choice_list = response.get_json()['question']['choices']

    random_possibly_correct_answer = choice_list[3]['id']
    response = client.post('/game', json={'token': token, 'answer': random_possibly_correct_answer})

    assert (response.get_json()['status'] == 'Success' and response.get_json()['message'] == 'A correct answer was submitted, and a new question has been created.' or response.get_json()['message'] == 'An incorrect answer was submitted, and the same question has been returned.')

def test_new_matt_game(client):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("DELETE FROM user")
    db.commit()
    cursor.execute("DELETE FROM game_session")
    db.commit()
    db.close()

    username = 'flask'
    password = 'willowtree'
    client.post('/signup', json={'username': username, 'password': password})
    response = client.post('/login', json={'username': username, 'password': password})
    token = response.get_json()['token']

    response = client.post('/game', json={'token': token, 'game_type': 'matt'})
    choice_list = response.get_json()['question']['choices']

    count = 0
    pass_test = True
    for choice in choice_list:
        if 'matt' in choice['choice']['alt'].lower() or 'matt' in choice['choice']['url']:
            count = count + 1

    assert count > 4