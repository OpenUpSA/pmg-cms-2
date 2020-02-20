from tests import PMGLiveServerTestCase
from pmg.models import db
from tests.fixtures import (
    dbfixture, UserData, RoleData
)


class TestAdminView(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminView, self).setUp()

        self.fx = dbfixture.data(
            RoleData, UserData, 
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestAdminView, self).tearDown()

    def test_admin_page_unauthorised(self):
        """
        Test admin page (/admin) unauthorised
        """
        self.make_request("/admin", follow_redirects=True)
        self.assertIn('Login now', self.html)

    def test_admin_page_authorised(self):
        """
        Test admin page (/admin) authorised
        """
        user = self.fx.UserData.admin
        self.make_request("/admin", user, follow_redirects=True)
        self.assertIn('Record counts', self.html)