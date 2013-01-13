from ConfigParser import SafeConfigParser
from hashlib import md5

import requests
from sanction.client import Client

from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from flask import Flask, redirect, request, session
app = Flask(__name__)
login_manager = LoginManager()
login_manager.setup_app(app)


config = SafeConfigParser()
config.read('config.ini')
client_id = config.get('credentials', 'client_id')
shared_secret = config.get('credentials', 'shared_secret')
app.secret_key = config.get('login', 'secret_key')

awful_database = {}

class User(UserMixin):
    def __init__(self, access_token):
        self.id = access_token
    def get_auth_token(self):
        return md5(self.get_id()).hexdigest()


def load_user(access_token):
    user = User(access_token)
    awful_database[user.get_auth_token()] = user.get_id()
    return user
login_manager.user_loader(load_user)

@login_manager.token_loader
def token_user(access_hash):
    return User(awful_database[access_hash])

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
    print current_user.get_id()
    response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/sections/c0b869f8403c3c1ddb1a4ffd0a25e5ed7349a7aa_id/studentSectionAssociations/getStudents',
        headers={
            'Accept': 'application/vnd.slc+json',
            'Content-Type': 'application/vnd.slc+json',
            'Authorization': 'bearer %s' % current_user.get_id()
        })
    print response.json()
    return "Hello! %s" % len(response.json())
    

@app.route('/callback')
def callback():
    client = Client(token_endpoint='https://api.sandbox.slcedu.org/api/oauth/token',
        resource_endpoint='https://api.sandbox.slcedu.org/api/rest/v1',
        client_id=client_id, client_secret=shared_secret,
        redirect_uri='http://slcgoals.cloudapp.net/callback')
    client.request_token(code=request.args['code'])
    access_token = client.access_token
    #TODO: load_user is NoneType. Just add to database and do this manually
    login_user(load_user(access_token))
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=True)