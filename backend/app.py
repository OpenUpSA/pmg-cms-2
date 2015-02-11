import logging
import logging.config
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import sys
import os
from flask_mail import Mail

env = os.environ.get('FLASK_ENV', 'development')

app = Flask(__name__, static_folder="not_static")
app.config.from_pyfile('../config/%s/config.py' % env)
db = SQLAlchemy(app)
mail = Mail(app)

# setup logging
with open('config/%s/logging.yaml' % env) as f:
    import yaml
    logging.config.dictConfig(yaml.load(f))


# override flask mail's send operation to inject some customer headers
original_send = mail.send
def send_email_with_subaccount(message):
    message.extra_headers = {'X-MC-Subaccount': app.config['MANDRILL_TRANSACTIONAL_SUBACCOUNT']}
    original_send(message)
app.extensions.get('mail').send = send_email_with_subaccount


import views
import admin
import helpers
