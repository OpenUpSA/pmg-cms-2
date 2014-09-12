import logging
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import sys

app = Flask(__name__, instance_relative_config=True, static_folder="not_static")
app.config.from_pyfile('config.py', silent=True)
db = SQLAlchemy(app)

# load log level from config
LOG_LEVEL = app.config['LOG_LEVEL']
LOGGER_NAME = app.config['LOGGER_NAME']

# create logger for this application
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(LOG_LEVEL)

# declare format for logging to file
file_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
)

# log to stdout
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(LOG_LEVEL)
stream_handler.setFormatter(file_formatter)
logger.addHandler(stream_handler)

# import drupal_models as models
# model_dict = models.generate_models()
# import admin

import views