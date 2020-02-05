from tests import PMGLiveServerTestCase
from mock import patch
import unittest
from pmg.models import db, User
from tests.fixtures import dbfixture, UserData


class TestAdminUsersPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminUsersPage, self).setUp()

        self.fx = dbfixture.data(UserData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminUsersPage, self).tearDown()

    def test_admin_users_page(self):
        """
        Test admin users page (/admin/user/)
        """
        self.make_request("/admin/user/", self.user, follow_redirects=True)
        self.assertIn("Users", self.html)
        self.assertIn(self.fx.UserData.admin.email, self.html)
        self.assertIn(self.fx.UserData.editor.email, self.html)
        self.assertIn(self.fx.UserData.inactive.email, self.html)
