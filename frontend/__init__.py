import logging
import logging.config
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import os

os.environ['PMG_LAYER'] = 'frontend'

env = os.environ.get('FLASK_ENV', 'development')

app = Flask(__name__, static_folder="static")
app.config.from_pyfile('../config/%s/config.py' % env)

db = SQLAlchemy(app)

# setup logging
with open('config/%s/logging.yaml' % env) as f:
    import yaml
    logging.config.dictConfig(yaml.load(f))


# setup assets
from flask.ext.assets import Environment, Bundle
assets = Environment(app)
assets.url_expire = False
assets.debug      = app.debug
# source files
assets.load_path  = ['%s/static' % app.config.root_path]

assets.register('css',
    Bundle(
      'resources/css/*.css',
      'font-awesome-4.2.0/css/font-awesome.min.css',
      'chosen/chosen.min.css',
      output='stylesheets/app.%(version)s.css'))

assets.register('js', Bundle(
    'bower_components/jquery/dist/jquery.min.js',
    'bower_components/bootstrap/js/tab.js',
    'bower_components/bootstrap/js/transition.js',
    'bower_components/bootstrap/js/alert.js',
    'bower_components/bootstrap/js/dropdown.js',
    'chosen/chosen.jquery.js',
    'resources/javascript/*.js',
    output='javascript/app.%(version)s.js'))


import views
import user_management
