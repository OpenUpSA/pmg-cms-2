from flask import Blueprint

api = Blueprint('backend', __name__)

import views
import admin
import helpers
