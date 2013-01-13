from ConfigParser import SafeConfigParser

import requests
from sanction.client import Client

from flask import Flask, redirect, request
app = Flask(__name__)


config = SafeConfigParser()
config.read('config.ini')
client_id = config.get('credentials', 'client_id')
shared_secret = config.get('credentials', 'shared_secret')


@app.route('/')
def root():
    client = Client(auth_endpoint='https://api.sandbox.slcedu.org/api/oauth/authorize',
        client_id=client_id, redirect_uri='http://slcgoals.cloudapp.net/callback')
    return redirect(client.auth_uri())

@app.route('/callback')
def callback():
    client = Client(token_endpoint='https://api.sandbox.slcedu.org/api/oauth/token',
        resource_endpoint='https://api.sandbox.slcedu.org/api/rest/v1',
        client_id=client_id, client_secret=shared_secret,
        redirect_uri='http://slcgoals.cloudapp.net/callback')
    print request.args['code']
    client.request_token(code=request.args['code'])
    access_token = client.access_token

    response = requests.get('https://api.sandbox.slcedu.org/api/rest/v1/teachers/537fab8373d843f3fedb7beab7c5988d628e2d17_id/teacherSectionAssociations/sections',
        headers={
            'Accept': 'application/vnd.slc+json',
            'Content-Type': 'application/vnd.slc+json',
            'Authorization': 'bearer %s' % access_token
        })
    print response.json()
    
    #print client.request('/sections')
    return "Working!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=True)