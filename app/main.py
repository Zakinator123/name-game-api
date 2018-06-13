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
    x = bcrypt.generate_password_hash('test').decode('utf-8')
    bool = bcrypt.check_password_hash(x, 'test')
    return (str(bool))


@app.route("/test_db_connection")
def db():
    db = MySQLdb.connect(os.environ['TESTDB_HOSTNAME'], os.environ['TESTDB_USERNAME'], os.environ['TESTDB_PASSWORD'], os.environ['TESTDB_DBNAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    sql = "SELECT * FROM user"
    cursor.execute(sql)
    db.close()
    test = cursor.fetchall()
    return jsonify(test)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
