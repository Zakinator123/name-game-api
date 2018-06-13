from flask import Flask
import MySQLdb
import MySQLdb.cursors
from flask import jsonify
import os
from flask_cors import CORS
from flask import request
import hmac
from functools import wraps
from flask_bcrypt import Bcrypt

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)


@app.route("/")
def home():
    return ("Welcome to the Name Game API!")


@app.route("/test_db_connection")
def db():
    db = MySQLdb.connect(os.environ['TESTDB_HOSTNAME'], os.environ['TESTDB_USERNAME'], os.environ['TESTDB_PASSWORD'], os.environ['TESTDB_DBNAME'])
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


    db = MySQLdb.connect(os.environ['TESTDB_HOSTNAME'], os.environ['TESTDB_USERNAME'], os.environ['TESTDB_PASSWORD'], os.environ['TESTDB_DBNAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Check if username already exists
    sql = "SELECT * FROM user WHERE username=%s"
    cursor.execute(sql, (username,))
    if cursor.rowcount > 0:
        return jsonify({'status': 'Error', 'message': 'Username already taken.'})

    sql = "INSERT INTO user (username, password) VALUES (%s, %s)"
    cursor.execute(sql, (username, password))
    db.commit()
    db.close()

    return jsonify({'status': 'Success', 'message': 'User successfully created!'})


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
