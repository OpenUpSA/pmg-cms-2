from tests import PMGLiveServerTestCase
from mock import patch
import unittest
from pmg.models import db, User
from tests.fixtures import dbfixture, UserData, RoleData, OrganisationData


class TestAdminUsersPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminUsersPage, self).setUp()

        self.fx = dbfixture.data(UserData, RoleData, OrganisationData)
        self.fx.setup()
        self.user = self.fx.UserData.admin
        self.create_user_data = {
            "email": "test@example.com",
            "name": "Test user",
            "active": "y",
            "roles": self.fx.RoleData.admin.id,
            "organisation": self.fx.OrganisationData.pmg.id,
            "expiry": "2065-02-06",
        }

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

    def test_admin_user_new_page(self):
        """
        Test admin get new user page (/admin/user/new)
        """
        url = "/admin/user/new"
        self.make_request(
            url, self.user, follow_redirects=True,
        )
        self.assertIn("Email", self.html)
        self.assertIn("Email address confirmed at", self.html)
        self.assertIn("Subscribe Daily Schedule", self.html)

    def test_post_admin_users_new_page(self):
        """
        Test admin new users page (/admin/user/new)
        """
        before_count = len(User.query.all())
        url = "/admin/user/new/?url=%2Fadmin%2Fuser%2F"
        response = self.make_request(
            url,
            self.user,
            data=self.create_user_data,
            method="POST",
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        after_count = len(User.query.all())
        self.assertLess(before_count, after_count)

        created_user = User.query.filter(
            User.email == self.create_user_data["email"]
        ).scalar()
        self.assertTrue(created_user)
        self.created_objects.append(created_user)
