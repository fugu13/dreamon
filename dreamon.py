from ConfigParser import SafeConfigParser

from sanction.client import Client

from flask import Flask, redirect
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=True)