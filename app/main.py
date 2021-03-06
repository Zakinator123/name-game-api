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
import json
import random
from functools import wraps
from flask_bcrypt import Bcrypt
import requests

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# API Dummy Home Page
@app.route("/")
def home():
    return ("Welcome to the Name Game API! This is the API Homepage")

# API Dummy DB Connection Test
@app.route("/test_db_connection")
def db():
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    sql = "SHOW TABLES"
    cursor.execute(sql)
    rowcount = cursor.rowcount
    db.close()
    return jsonify({'table_count': rowcount})


@app.route("/signup", methods=['POST'])
def signup():
    """
        Takes a username and password and saves it to database if username is not taken. Does not log user in.

        POST parameters (application/json encoding)
        ----------
        {
            "username": <A username string>,
            "password": <A password string>,
        }

        Returns (application/json encoding)
        -------
        {
            "status" : <"Success" | "Error">,
            "message" : <A string with helpful error information>
        }
    """

    if 'username' in request.get_json() and 'password' in request.get_json():
        username = request.get_json()['username']
        password = request.get_json()['password']
    else:
        return jsonify({'status': 'Error', 'message': 'Appropriate signup credentials were not provided.'})

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
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
    """
        Takes a username and password. If credentials are correct, returns an authenticator token.

        POST parameters (application/json encoding)
        ----------
        {
            "username": <A username string>,
            "password": <A password string>,
        }

        Returns (application/json encoding)
        -------
        {
            "status" : <"Success" | "Error">,
            "message" : <A string with helpful error information>,
            "token" : <Some long random string>
        }
    """

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
        cursor.execute(sql, (username,))
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
        cursor.execute(sql, (username,))

        if cursor.rowcount > 0:
            authenticator_row = cursor.fetchone()
            authenticator_timestamp = authenticator_row['timestamp']

            then = datetime.datetime.strptime(authenticator_timestamp, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            then = time.mktime(then.timetuple())
            now = time.mktime(now.timetuple())

            # If the authenticator token's age is less than 3 minutes, reuse the current authenticator.
            if ((int(now - then) / 60) < 3):
                return jsonify(
                    {'status': 'Success', 'token': authenticator_row['token'], 'message': 'Successfully logged in.'})
            else:
                # Otherwise, generate a new random authenticator token for the user to replace the old one.
                auth_token = str(secrets.token_urlsafe())

                # Overwrite the old authenticator token in the database.
                now = str(datetime.datetime.now())[:19]
                sql = "UPDATE authenticator SET timestamp=%s, token=%s WHERE username=%s"
                cursor.execute(sql, (now, auth_token, username))
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


def authenticated_required(f):
    @wraps(f)
    def check_authenticator(*args, **kwargs):
        """
            Decorator for other views that require a user to be logged in.
            Takes a token and determines if it's valid (e.g. not expired).
             If token valid, the desired API endpoint will proceed to execute, otherwise returns an error.

            POST parameters (application/json encoding)
            ----------
            {
                "token" : <A token string>
            }

            Returns
            -------
            If the presented token is valid, this function returns the original function a user tried to
            execute (it is not an endpoint itself). Otherwise, it returns an error (in application/json encoding).
        """
        post_body = request.get_json()

        if 'token' in post_body:
            token = post_body['token']
        else:
            return jsonify({'status': 'Error',
                            'message': "No authenticator token was provided. Please use the login API to receive one."})

        db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                             os.environ['RDS_DB_NAME'])
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Check if user is already logged in:
        sql = "SELECT * FROM authenticator WHERE token=%s"
        cursor.execute(sql, (token, ))

        if cursor.rowcount > 0:
            authenticator_data = cursor.fetchone()

            authenticator_timestamp = authenticator_data['timestamp']

            then = datetime.datetime.strptime(authenticator_timestamp, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            then = time.mktime(then.timetuple())
            now = time.mktime(now.timetuple())

            # If the authenticator token's age is less than 3 minutes, refresh the token's age and continue.
            if ((int(now - then) / 60) < 3):
                sql = "UPDATE authenticator SET timestamp=%s WHERE token=%s"
                now = str(datetime.datetime.now())[:19]
                cursor.execute(sql, (now, authenticator_data['token']))
                db.commit()
                db.close()

                return f(*args, **kwargs)
            else:
                return jsonify({'status': 'Error', 'message': 'Session Expired.'})
        else:
            return jsonify({'status': 'Error', 'message': 'Invalid authentication token.'})

    return check_authenticator



@app.route("/logout", methods=['POST'])
@authenticated_required
def logout():
    """
        Takes an authenticator token. Deletes it from database if it exists.

        POST parameters (application/json encoding)
        ----------
        {
            "token": <A token string>
        }

        Returns (application/json encoding)
        -------
        {
            "status" : <"Success" | "Error">,
            "message" : <A string with helpful error information>,
        }
    """
    post_body = request.get_json()

    token = post_body['token']
    __stop_game(token)

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    sql = "DELETE FROM authenticator WHERE token=%s"
    cursor.execute(sql, (token,))
    db.commit()
    db.close()

    return jsonify({'status': 'Success', 'message': 'Successfully logged out.'})




@app.route("/game", methods=['POST'])
@authenticated_required
def game():
    """
        This endpoint contains the primary name-game functionality. It takes two parameters, a token and either a
        'game_type' (if the user wants to start a new game session) or an 'answer' (if the user wants to submit an answer
        to the current question in his/her current active game session) and returns the output below depending on the input.

        POST parameters (application/json encoding)
        ----------
        {
            "token": <A token string>,
            <"game_type" | "answer"> : <string containing either an answer id or the name of a new game type ("standard" | "reverse" | "matt")>
        }

        Returns (application/json encoding)
        -------
        {
            "message" : <A string with helpful error/success information>,
            "status" : <"Success" | "Error">,
            "last_answer_submission": <"None" | "Correct" | "Incorrect">,
            "game_type": <game_type string>,
            "question": {
                "choice_type": <"image" | "text">,
                "choices": [
                    {
                        "choice": < Dictionary/JSON Object containing image information | Full Name >,
                        "id": <Some ID uniquely identifying the choice"
                    },
                    ...
                ],
                "question_image": {<If the choice_type is text (reverse mode), then image information will be in this dictionary>},
                "question_text": <String containing question text>
            },
            "session_number_right": <number>,
            "session_number_wrong": <number>,
            "status": <"Success" | "Error">
        }
    """

    post_body = request.get_json()

    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Get username
    cursor.execute("SELECT * FROM authenticator WHERE token=%s", (post_body['token'], ))
    authenticator_data = cursor.fetchone()

    new_game = False
    game_type_data = None

    # Start a new game
    if 'game_type' in post_body:
        sql = "SELECT * FROM game_type WHERE game_name=%s"
        cursor.execute(sql, (post_body['game_type'],))
        if cursor.rowcount == 0:
            return jsonify({'status': 'Error', 'message': 'Invalid Game Type.'})
        else:
            game_type_data = cursor.fetchone()

        new_game = True

        # Stop previous game session if one exists if new game type is provided
        __stop_game(post_body['token'])

    else:
    # Answer to previous game question should be in post body. Return error if there is no answer.
        if 'answer' not in post_body:
            return jsonify({'status': "Error", "message" : "Invalid input - include in the POST body either a 'game_type' (to start a new game) or an 'answer' (to continue a game)."})
        else:
            answer = post_body['answer']
            sql = "SELECT * FROM game_session WHERE username=%s AND current_session IS TRUE"
            cursor.execute(sql, (authenticator_data['username'],))
            if (cursor.rowcount == 0):
                return jsonify({"status": "Error", "message" : "There is no active game session under your account. Call this endpoint with a game type parameter to start a new game"})
            game_session_data = cursor.fetchone()
            # Check if submitted answer is correct. If not, update session stats and return question again.
            if (game_session_data['current_question_answer'] != answer):
                cursor.execute("UPDATE game_session SET number_wrong = number_wrong + 1 WHERE username=%s AND current_session IS TRUE", (authenticator_data['username'], ))
                db.commit()
                return jsonify({
                    'status': 'Success',
                    'message': 'An incorrect answer was submitted, and the same question has been returned.',
                    'game_type': game_session_data['game_type'],
                    'question': json.loads(game_session_data['current_question']),
                    'session_number_right': int(game_session_data['number_right']),
                    'session_number_wrong': int(game_session_data['number_wrong']) + 1,
                    'last_answer_submission' : 'Incorrect'
                })

    # At this point, the user either is starting a new game, or is submitting a correct answer
    # In both cases, we must provide the user with a new question+choices - this is calculated below.

    # If game type data wasn't retrieved above, then this user has an active game session.
    # Hence, we can retrieve the game type data via the authenticator.
    if not game_type_data:
        sql = "SELECT * FROM game_session WHERE username=%s AND current_session IS TRUE"
        cursor.execute(sql, (authenticator_data['username'], ))
        game_name = cursor.fetchone()['game_type']
        sql = "SELECT * FROM game_type WHERE game_name=%s"
        cursor.execute(sql, (game_name, ))
        game_type_data = cursor.fetchone()

    # Willowtree API call. Perhaps should be in a try/except?
    r = requests.get('https://www.willowtreeapps.com/api/v1.0/profiles')
    employees = r.json()

    final_list_of_employees = []

    ### STANDARD OR REVERSE MODE - GET 6 RANDOM EMPLOYEES
    if game_type_data['game_name'] == 'standard' or game_type_data['game_name'] == 'reverse':
        employee_ids = []
        count = 0
        while count < game_type_data['num_choices']:
            employee = employees[random.randint(0, len(employees) - 1)]
            if (employee['id'] not in employee_ids):
                employee_ids.append(employee['id'])
                final_list_of_employees.append(employee)
                count = count + 1

    ### NAME FILTERING MODE - (Only Matt mode for now)
    else:
        preliminary_list_of_employees = []
        if game_type_data['name_filter']:
            # 'Matt' is the only name filter at this point.
            name_filter = game_type_data['name_filter']
            for employee in employees:
                if name_filter in employee['firstName'].lower():
                    preliminary_list_of_employees.append(employee)

            employee_ids = []
            count = 0
            while count < game_type_data['num_choices']:
                employee = preliminary_list_of_employees[random.randint(0, len(preliminary_list_of_employees) - 1)]
                if (employee['id'] not in employee_ids):
                    employee_ids.append(employee['id'])
                    final_list_of_employees.append(employee)
                    count = count + 1

    solution_employee = final_list_of_employees[random.randint(0, len(final_list_of_employees) - 1)]

    # This next section determines and calculates what "choices" (e.g. images, or text names) goes into the JSON response.
    question_text = ''
    question_image = {}
    solution_id = ''
    choices = []

    if game_type_data['choice_type'] == 'image':
        for employee in final_list_of_employees:
            choices.append({'id': employee['headshot']['id'], 'choice': employee['headshot']})

        question_text = "Who is " + solution_employee['firstName'] + " " + solution_employee['lastName']
        solution_id = solution_employee['headshot']['id']

    elif game_type_data['choice_type'] == 'text':
        # Name Choices
        for employee in final_list_of_employees:
            choices.append({'id': employee['id'], 'choice': employee['firstName'] + " " + employee['lastName']})

        question_text = "Who is in this picture?"
        question_image = solution_employee['headshot']
        solution_id = solution_employee['id']


    question_dictionary = {
        'question_text': question_text,
        'question_image': question_image,
        'choice_type': game_type_data['choice_type'],
        'choices': choices
    }


    if new_game:
        sql = "INSERT INTO game_session (username, game_type, number_right, number_wrong, current_question, current_session, current_question_answer) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (authenticator_data['username'], game_type_data['game_name'], 0, 0, json.dumps(question_dictionary), True, str(solution_id)))
        db.commit()
        db.close()
        return jsonify({
            'status': 'Success',
            'message': 'A new game was created, and a new question has been created.',
            'game_type': game_type_data['game_name'],
            'question': question_dictionary,
            'session_number_right': 0,
            'session_number_wrong': 0,
            'last_answer_submission': 'None'
        })
    else:
        # User submitted a correct answer! Update stats accordingly and respond with the new question data.
        sql = "UPDATE game_session SET number_right = number_right + 1, current_question=%s, current_question_answer=%s WHERE username=%s AND current_session IS TRUE"
        cursor.execute(sql, (json.dumps(question_dictionary), str(solution_id), authenticator_data['username']))
        db.commit()
        sql = "SELECT * FROM game_session WHERE username=%s AND current_session IS TRUE"
        cursor.execute(sql, (authenticator_data['username'],))
        game_session_data = cursor.fetchone()

        db.close()
        return jsonify({
            'status': 'Success',
            'message': 'A correct answer was submitted, and a new question has been created.',
            'game_type': game_session_data['game_type'],
            'question': json.loads(game_session_data['current_question']),
            'session_number_right': int(game_session_data['number_right']),
            'session_number_wrong': int(game_session_data['number_wrong']),
            'last_answer_submission': 'Correct'
        })

@app.route("/stop_game", methods=['POST'])
@authenticated_required
def stop_game():
    """
        Takes an authenticator token and sets any game sessions associated with you to NOT be current anymore.

        POST parameters (application/json encoding)
        ----------
        {
            "token": <A token string>
        }

        Returns (application/json encoding)
        -------
        {
            "status" : <"Success" | "Error">,
            "message" : <A string with helpful error information>,
        }
    """
    post_body = request.get_json()
    token = post_body['token']

    __stop_game(token)
    return jsonify({"status" : "Success", "message" : "You have no active game sessions."})


@app.route("/leaderboard", methods=['GET'])
def leaderboard():
    """
        No parameters required. Returns an ordered list (descending) of sessions based on their score, which
        is calculated by subtracting the number of wrong questions from the number of right questions.

        Returns (application/json encoding)
        -------
        {
            "status" : <"Success" | "Error">,
            "message" : <A string with helpful error information>,
            "leaderboard" : [
                {
                    "game_type": <game type>,
                    "number_right": <integer>,
                    "number_wrong": <integer>,
                    "session_id": <id>,
                    "username": <username string>
                },
                { ... },
                ...
            ]
        }
    """
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    sql = "SELECT username, game_type, number_right, number_wrong, session_id FROM game_session ORDER BY (number_right - number_wrong) LIMIT 20"
    cursor.execute(sql)

    if cursor.rowcount == 0:
        return jsonify({'status': 'Error', 'message': 'There was no leaderboard to display.'})
    else:
        leaderboard = cursor.fetchall()
        return jsonify({'status' : "Success", 'message' : "Top 20 game sessions in order (score based on number_right subtracted from number_wrong).", 'leaderboard' : leaderboard})


# This is a helper function for the stop_game endpoint above.
def __stop_game(token):
    db = MySQLdb.connect(os.environ['RDS_HOSTNAME'], os.environ['RDS_USERNAME'], os.environ['RDS_PASSWORD'],
                         os.environ['RDS_DB_NAME'])
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    sql = "SELECT * FROM authenticator WHERE token=%s"
    cursor.execute(sql, (token, ))
    username = cursor.fetchone()['username']

    sql = "UPDATE game_session SET current_session=0 WHERE username=%s"
    cursor.execute(sql, (username, ))
    db.commit()
    db.close()

    return True


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)




