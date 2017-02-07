# setup testing environment
import os
os.environ['FLASK_ENV'] = 'test'

from pmg import app
from pmg.models import db
from flask_testing import TestCase


class PMGTestCase(TestCase):
    def create_app(self):
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
