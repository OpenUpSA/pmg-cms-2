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

import views
import user_management
