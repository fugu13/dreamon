import json
import shelve
import bsddb
import os.path
from ConfigParser import SafeConfigParser
from hashlib import md5

import requests
from sanction.client import Client
from werkzeug import secure_filename

from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from flask import Flask, flash, redirect, request, session, render_template
app = Flask(__name__)
login_manager = LoginManager()
login_manager.setup_app(app)
app.config['UPLOAD_FOLDER'] = '/home/azureuser/dreamon/static/images'


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
    journey = database.get(str('journey' + identifier), [])
    start = journey[0] if journey else None
    rest = journey[1:]
    return render_template('assist.html', student=student, start=start, rest=rest)

@app.route('/step/<identifier>', methods=['GET', 'POST'])
def step(identifier):
    if request.method == 'POST':
        journey = database.get(str('journey' + identifier), [])
        accomplishment = request.form.get('accomplishment', 'None')
        prompt = request.form.get('prompt', 'None')

        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if not journey:
            journey = [{}]

        objective = {
            'academicSubject': 'Miscellaneous',
            'description': prompt,
            'objective': prompt[:59],
            'objectiveGradeLevel': 'Ungraded'
        }
        response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/learningObjectives',
            headers={
                'Accept': 'application/vnd.slc+json',
                'Content-Type': 'application/vnd.slc+json',
                'Authorization': 'bearer %s' % current_user.get_id()
            }, data=json.dumps(objective))
        #I would love to tie this to the student, but haven't yet;
        #that part of the API feels very awkward, with various requirements
        #that make it hard to do things that are looser (but no less important
        #to record), such as student-set objectives
        print response.status_code, response.text
        journey[-1]['accomplishment'] = accomplishment
        journey[-1]['image'] = filename
        journey.append({'prompt': prompt})
        database[str('journey' + identifier)] = journey
        return redirect('/step/' + identifier)
    else:
        student = database.get(str(identifier), {})
        journey = database.get(str('journey' + identifier), [])
        prompt = journey[-1]['prompt'] if journey else "What's your dream?"
        goal = journey[0]['accomplishment'] if journey else None
        return render_template('step.html', student=student, prompt=prompt, goal=goal)

@app.route('/suggest/<identifier>', methods=['GET', 'POST'])
def suggest(identifier):
    if request.method == 'POST':
        suggestions = request.form.getlist('course')
        print suggestions
        database[str('suggest' + identifier)] = suggestions
        flash('Suggestions Saved!')
        return redirect('/suggest/%s' % identifier)
    else:
        student = database[str(identifier)]
        suggestions = frozenset(database.get(str('suggest' + identifier), []))
        print suggestions
        #okay, get list of clubs, courses, check ones of interest, click recommend.
        #check ones already checked

        response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/courses',
            headers={
                'Accept': 'application/vnd.slc+json',
                'Content-Type': 'application/vnd.slc+json',
                'Authorization': 'bearer %s' % current_user.get_id()
            })
        courses = response.json()

        return render_template('courses.html', suggestions=suggestions, courses=courses, student=student)

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