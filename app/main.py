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



if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)


# #     # Get current datetime (truncating decimal seconds)
#     then = str(datetime.datetime.now())[:19]
#     time.sleep(3)
#
#     now = datetime.datetime.now()
#
#     then_datetime = datetime.datetime.strptime(then, '%Y-%m-%d %H:%M:%S')
#
#     now = time.mktime(now.timetuple())
#     then = time.mktime(then_datetime.timetuple())