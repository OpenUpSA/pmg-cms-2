import logging
import logging.config
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import sys
import os

env = os.environ.get('FLASK_ENV', 'development')

app = Flask(__name__, static_folder="not_static")
app.config.from_pyfile('../config/%s/config.py' % env)
db = SQLAlchemy(app)

# setup logging
with open('config/%s/logging.yaml' % env) as f:
    import yaml
    logging.config.dictConfig(yaml.load(f))

# import drupal_models as models
# model_dict = models.generate_models()
# import admin

import views
import admin
