from tests import PMGLiveServerTestCase
from pmg.models import db, User
from tests.fixtures import (dbfixture, UserData, RoleData)
from flask_security.utils import encrypt_password


class TestLoginPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestLoginPage, self).setUp()

        self.fx = dbfixture.data(
            RoleData,
            UserData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestLoginPage, self).tearDown()

    def test_view_login(self):
        """
        Test view login (/user/login).
        """
        response = self.make_request("/user/login/",
                                     follow_redirects=True)
        self.assertEqual(200, response.status_code)
        self.assertIn('Login now to view premium content', self.html)
        self.assertIn('Email Address', self.html)
        self.assertIn('Password', self.html)

    def test_submit_login(self):
        """
        Test submit login (/user/login).
        """
        user = User.query.first()
        password = 'password'
        user.password = encrypt_password(password)
        data = {'email': user.email, 'password': password}
        response = self.make_request("/user/login/",
                                     follow_redirects=True,
                                     method="POST",
                                     data=data)
        self.assertEqual(200, response.status_code)
        self.assertIn('Log Out', self.html)
