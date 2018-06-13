from flask import Flask
import MySQLdb
import MySQLdb.cursors
from flask import jsonify
import os
from flask_cors import CORS
from flask import request
import datetime
import secrets
import time
from functools import wraps
from flask_bcrypt import Bcrypt

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)


@app.route("/")
def home():
    return ("Welcome to the Name Game API! This is the API Homepage")


@app.route("/test_db_connection")
def db():
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'], os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    sql = "SHOW TABLES"
    cursor.execute(sql)
    rowcount = cursor.rowcount
    db.close()
    return jsonify({'table_count': rowcount})


@app.route("/signup", methods=['POST'])
def signup():

    if 'username' in request.get_json() and 'password' in request.get_json():
        username = request.get_json()['username']
        password = request.get_json()['password']
    else:
        return jsonify({'status': 'Error', 'message': 'Appropriate signup credentials were not provided.'})


    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'], os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Check if username already exists
    sql = "SELECT * FROM user WHERE username=%s"
    cursor.execute(sql, (username,))
    if cursor.rowcount > 0:
        return jsonify({'status': 'Error', 'message': 'Username already taken.'})

    sql = "INSERT INTO user (username, password) VALUES (%s, %s)"
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute(sql, (username, hashed_password))
    db.commit()
    db.close()

    return jsonify({'status': 'Success', 'message': 'User successfully created!'})

@app.route("/login", methods=['POST'])
def login():

    if 'username' in request.get_json() and 'password' in request.get_json():
        username = request.get_json()['username']
        plain_text_password = request.get_json()['password']
    else:
        return jsonify({'status': 'Error', 'message': 'Appropriate login credentials were not provided.'})

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Check if username exists
    try:
        sql = "SELECT * FROM user WHERE username=%s"
        cursor.execute(sql, (username, ))
        if (cursor.rowcount == 0):
            raise Exception
    except:
        return jsonify({'status': 'Error', 'message': 'User does not exist.'})

    # Check if password is correct
    user_password_hash = cursor.fetchone()['password']
    password_matches = bcrypt.check_password_hash(user_password_hash, plain_text_password)

    if password_matches:
        # Check if the user already has a non-expired authenticator
        sql = "SELECT * FROM authenticator WHERE username=%s"
        cursor.execute(sql, (username, ))

        if cursor.rowcount > 0:
            authenticator_row = cursor.fetchone()
            authenticator_timestamp = authenticator_row['timestamp']

            then = datetime.datetime.strptime(authenticator_timestamp, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            then = time.mktime(then.timetuple())
            now = time.mktime(now.timetuple())

            # If the authenticator token's age is less than 3 minutes, reuse the current authenticator.
            if ((int(now - then) / 60) < 3):
                return jsonify({'status': 'Success', 'token': authenticator_row['token'], 'message': 'Successfully logged in.'})
            else:
            # Otherwise, generate a new random authenticator token for the user to replace the old one.
                auth_token = str(secrets.token_urlsafe())

                # Overwrite the old authenticator token in the database.
                sql = "UPDATE authenticator SET timestamp=%s WHERE username=%s)"
                cursor.execute(sql,(str(now)[:19], username))
                db.commit()
                db.close()

                return jsonify({'status': 'Success', 'token': auth_token, 'message': 'Successfully logged in.'})
        else:
            # There was no previous authenticator for this user, so create a new one.
            auth_token = str(secrets.token_urlsafe())
            now = datetime.datetime.now()

            # Save the authenticator token to the database.
            sql = "INSERT INTO authenticator (token, username, timestamp) VALUES (%s, %s, %s)"
            cursor.execute(sql, (auth_token, username, str(now)[:19]))
            db.commit()
            db.close()
            return jsonify({'status': 'Success', 'token': auth_token, 'message': 'Successfully logged in.'})
    else:
        return jsonify({'status': 'Error', 'message': 'Incorrect password.'})

# TODO: Call the stop_game method from this view once it's implemeneted.
@app.route("/logout", methods=['POST'])
def logout():
    post_body = request.get_json()

    if 'token' in post_body:
        token = post_body['token']
    else:
        return jsonify({'status': 'Error', 'message': "No authenticator token was provided."})

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    sql = "DELETE FROM authenticator WHERE token=%s"
    cursor.execute(sql, (token,))
    db.commit()
    db.close()

    return jsonify({'status': 'Success', 'message': 'Successfully logged out.'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)


def authenticated_required(f):
    @wraps(f)
    def check_authenticator(*args, **kwargs):
        post_body = request.get_json()

        if 'token' in post_body:
            token = post_body['token']
        else:
            return jsonify({'status': 'Error', 'message': "No authenticator token was provided. Please use the login API to receive one."})

        db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                             os.environ['RDS_DB_NAME'])
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Check if user is already logged in:
        sql = "SELECT * FROM authenticator WHERE token=%s" % (post_body['token'])
        cursor.execute(sql)
        db.close()

        if cursor.rowcount > 0:
            authenticator_data = cursor.fetchone()

            authenticator_timestamp = authenticator_data['timestamp']

            then = datetime.datetime.strptime(authenticator_timestamp, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            then = time.mktime(then.timetuple())
            now = time.mktime(now.timetuple())

            # If the authenticator token's age is less than 3 minutes, refresh the token's age and continue.
            if ((int(now - then) / 60) < 3):
                sql = "UPDATE authenticator SET timestamp=%s WHERE token=%s)"
                cursor.execute(sql, (str(now)[:19], authenticator_data['token']))
                db.commit()
                db.close()

                return f(*args, **kwargs)
            else:
                return jsonify({'Status': 'Error', 'message': 'Session Expired.'})
        else:
            return jsonify({'Status': 'Error', 'message': 'Invalid authentication.'})
    return check_authenticator


@app.route("/start_game", methods=['POST'])
@authenticated_required
def start_game():
    pass

@app.route("/stop_game", methods=['POST'])
@authenticated_required
def stop_game():
    pass


@app.route("/submit_answer", methods=['POST'])
@authenticated_required
def submit_answer():
    pass


@app.route("/get_game_leaderboard", methods=['POST'])
@authenticated_required
def get_game_leaderboard():
    pass

