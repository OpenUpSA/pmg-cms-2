import logging
import logging.config
import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
from flask_mail import Mail

os.environ['PMG_LAYER'] = 'frontend'

env = os.environ.get('FLASK_ENV', 'development')

app = Flask(__name__, static_folder="static")
app.config.from_pyfile('../config/%s/config.py' % env)

db = SQLAlchemy(app)
CsrfProtect(app)
mail = Mail(app)

# setup logging
with open('config/%s/logging.yaml' % env) as f:
    import yaml
    logging.config.dictConfig(yaml.load(f))


# override flask mail's send operation to inject some customer headers
original_send = mail.send
def send_email_with_subaccount(message):
    message.extra_headers = {'X-MC-Subaccount': app.config['MANDRILL_TRANSACTIONAL_SUBACCOUNT']}
    print message
    #original_send(message)
app.extensions.get('mail').send = send_email_with_subaccount


# setup assets
from flask.ext.assets import Environment, Bundle
assets = Environment(app)
assets.url_expire = False
assets.debug      = app.debug
# source files
assets.load_path  = ['%s/static' % app.config.root_path]

from webassets.filter.pyscss import PyScss

assets.register('css',
    Bundle(
      'font-awesome-4.2.0/css/font-awesome.min.css',
      'chosen/chosen.min.css',
      Bundle(
        'resources/css/style.scss',
        'resources/css/bill-progress.scss',
        filters=PyScss(load_paths=assets.load_path),
        output='stylesheets/styles.%(version)s.css'),
      output='stylesheets/app.%(version)s.css'))

assets.register('js', Bundle(
    'bower_components/jquery/dist/jquery.min.js',
    'bower_components/bootstrap-sass/assets/javascripts/bootstrap.min.js',
    'chosen/chosen.jquery.js',
    'resources/javascript/users.js',
    'resources/javascript/members.js',
    'resources/javascript/pmg.js',
    output='javascript/app.%(version)s.js'))

assets.register('admin-js', Bundle(
    'resources/javascript/admin/admin.js',
    'resources/javascript/admin/email_alerts.js',
    output='javascript/admin.%(version)s.js'))


import helpers
import views
import user_management

from backend.app import api

app.register_blueprint(api, subdomain='api')
