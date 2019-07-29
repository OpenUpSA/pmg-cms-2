from tests import PMGLiveServerTestCase
from pmg.models import db
from tests.fixtures import (
    dbfixture, UserData, RoleData
)


class TestAdminView(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminView, self).setUp()

        self.fx = dbfixture.data(
            RoleData,UserData, 
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestAdminView, self).tearDown()

    def test_admin_page_unauthorised(self):
        """
        Test admin page (http://pmg.test:5000/admin)
        """
        self.get_page_contents("http://pmg.test:5000/admin")
        self.assertIn('Login now', self.html)

    def test_admin_page_authorised(self):
        """
        Test admin page (http://pmg.test:5000/admin)
        """
        user = self.fx.UserData.admin
        self.get_page_contents_as_user(user, "http://pmg.test:5000/admin")
        self.assertIn('Record counts', self.html)