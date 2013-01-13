import json
import shelve
import bsddb
from ConfigParser import SafeConfigParser
from hashlib import md5

import requests
from sanction.client import Client

from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from flask import Flask, redirect, request, session, render_template
app = Flask(__name__)
login_manager = LoginManager()
login_manager.setup_app(app)


config = SafeConfigParser()
config.read('config.ini')
client_id = config.get('credentials', 'client_id')
shared_secret = config.get('credentials', 'shared_secret')
app.secret_key = config.get('login', 'secret_key')

database = shelve.BsdDbShelf(bsddb.hashopen('database.db'))

class User(UserMixin):
    def __init__(self, access_token):
        self.id = access_token
    def get_auth_token(self):
        return md5(self.get_id()).hexdigest()


def load_user(access_token):
    user = User(access_token)
    database[user.get_auth_token()] = user.get_id()
    return user
login_manager.user_loader(load_user)

@login_manager.token_loader
def token_user(access_hash):
    return User(database[access_hash])

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

@app.route('/login')
def login():
    client = Client(auth_endpoint='https://api.sandbox.slcedu.org/api/oauth/authorize',
        client_id=client_id, redirect_uri='http://slcgoals.cloudapp.net/callback')
    return redirect(client.auth_uri())

@app.route('/')
@login_required
def root():
    response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/sections/44db6919c253745e4c78c6f903a57401ac26c4a3_id/studentSectionAssociations/students',
        headers={
            'Accept': 'application/vnd.slc+json',
            'Content-Type': 'application/vnd.slc+json',
            'Authorization': 'bearer %s' % current_user.get_id()
        })
    students = response.json()
    for student in students:
        database[str(student['id'])] = student
    return render_template('students.html', students=students)
    

@app.route('/assist/<identifier>')
def assist(identifier):
    student = database[str(identifier)]
    #okay, get list of clubs, courses, check ones of interest, click recommend.
    #check ones already checked
    programs = [dict(zip(['programId', 'programType'], details))
        for details in [
            ('Profokiev Society', 'Other')
        ]
    ]
    print programs
    for program in programs:
        response = requests.post('https://api.sandbox.slcedu.org/api/rest/v1/programs',
            headers={
                'Accept': 'application/vnd.slc+json',
                'Content-Type': 'application/vnd.slc+json',
                'Authorization': 'bearer %s' % current_user.get_id()
            }, data=json.dumps(program))
        print response.status_code, response.text

    response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/programs',
        headers={
            'Accept': 'application/vnd.slc+json',
            'Content-Type': 'application/vnd.slc+json',
            'Authorization': 'bearer %s' % current_user.get_id()
        })
    return json.dumps(response.json(), indent=2)

@app.route('/student/<identifier>')
def student(identifier):
    student = database[str(identifier)]



@app.route('/callback')
def callback():
    client = Client(token_endpoint='https://api.sandbox.slcedu.org/api/oauth/token',
        resource_endpoint='https://api.sandbox.slcedu.org/api/rest/v1',
        client_id=client_id, client_secret=shared_secret,
        redirect_uri='http://slcgoals.cloudapp.net/callback')
    client.request_token(code=request.args['code'])
    access_token = client.access_token
    login_user(load_user(access_token))
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=True)