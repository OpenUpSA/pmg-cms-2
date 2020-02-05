from tests import PMGLiveServerTestCase
from mock import patch
import unittest
from pmg.models import db, User
from tests.fixtures import dbfixture, UserData, OrganisationData


class TestAdminOrganisationsPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminOrganisationsPage, self).setUp()

        self.fx = dbfixture.data(UserData, OrganisationData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminOrganisationsPage, self).tearDown()

    def test_admin_organisations_page(self):
        """
        Test admin organisations page (/admin/organisation/)
        """
        self.make_request("/admin/organisation/", self.user, follow_redirects=True)
        self.assertIn("Organisations", self.html)
        self.assertIn(self.fx.OrganisationData.pmg.name, self.html)
        self.assertIn(self.fx.OrganisationData.pmg.domain, self.html)
