import unittest
from nose.tools import *  # noqa
import datetime

from pmg.models import db, User


class TestUser(unittest.TestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_expiry(self):
        u = User()
        u.expiry = datetime.date(2010, 1, 1)
        assert_true(u.has_expired())

        u.expiry = datetime.date.today() + datetime.timedelta(days=2)
        assert_false(u.has_expired())
