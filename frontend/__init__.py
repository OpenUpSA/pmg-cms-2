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


import views
import user_management
