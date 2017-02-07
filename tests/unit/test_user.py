from nose.tools import *  # noqa
import datetime

from pmg.models import User
from tests import PMGTestCase


class TestUser(PMGTestCase):
    def test_expiry(self):
        u = User()
        u.expiry = datetime.date(2010, 1, 1)
        assert_true(u.has_expired())

        u.expiry = datetime.date.today() + datetime.timedelta(days=2)
        assert_false(u.has_expired())
