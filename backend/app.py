import logging
import logging.config
from flask import Blueprint
from flask.ext.sqlalchemy import SQLAlchemy
import sys
import os

env = os.environ.get('FLASK_ENV', 'development')

#app = Flask(__name__, static_folder="not_static")
#app.config.from_pyfile('../config/%s/config.py' % env)
#db = SQLAlchemy(app)
api = Blueprint('backend', __name__)

# setup logging
with open('config/%s/logging.yaml' % env) as f:
    import yaml
    logging.config.dictConfig(yaml.load(f))

#UPLOAD_PATH = api.config['UPLOAD_PATH']
#if not os.path.isdir(UPLOAD_PATH):
#    os.mkdir(UPLOAD_PATH)


import views
import admin
import helpers
