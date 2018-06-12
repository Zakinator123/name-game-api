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


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
