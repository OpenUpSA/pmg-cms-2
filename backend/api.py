from flask import Blueprint

api = Blueprint('backend', __name__)

import views
import helpers
