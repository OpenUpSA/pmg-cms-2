from tests import PMGLiveServerTestCase
from mock import patch
import unittest
from pmg.models import db, User, Organisation
from tests.fixtures import dbfixture, UserData, OrganisationData, CommitteeData


class TestAdminOrganisationsPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminOrganisationsPage, self).setUp()

        self.fx = dbfixture.data(UserData, OrganisationData, CommitteeData)
        self.fx.setup()
        self.user = self.fx.UserData.admin
        self.create_organisation_data = {
            "name": "Test organisation",
            "domain": "Test domain",
            "contact": "test@example.com",
            "paid_subscriber": "y",
            "expiry": "2065-02-06",
            "subscriptions": self.fx.CommitteeData.communications.id,
            "users": self.fx.UserData.editor.id,
        }

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

    def test_admin_organisation_new_page(self):
        """
        Test admin get new organisation page (/admin/organisation/new)
        """
        url = "/admin/organisation/new"
        self.make_request(
            url, self.user, follow_redirects=True,
        )
        self.assertIn("Name", self.html)
        self.assertIn("Domain", self.html)

    def test_post_admin_organisations_new_page(self):
        """
        Test admin new organisations page (/admin/organisation/new)
        """
        before_count = len(Organisation.query.all())
        url = "/admin/organisation/new/?url=%2Fadmin%2Forganisation%2F"
        response = self.make_request(
            url,
            self.user,
            data=self.create_organisation_data,
            method="POST",
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        after_count = len(Organisation.query.all())
        self.assertLess(before_count, after_count)

        created_organisation = Organisation.query.filter(
            Organisation.name == self.create_organisation_data["name"]
        ).scalar()
        self.assertTrue(created_organisation)
        self.created_objects.append(created_organisation)

    def test_admin_organisation_view_edit_page(self):
        """
        Test admin view edit organisation page (/admin/organisation/edit)
        """
        url = "/admin/organisation/edit/?id=%d"
        organisation = self.fx.OrganisationData.pmg
        self.make_request(
            url % organisation.id, self.user, follow_redirects=True,
        )
        self.assertIn(organisation.name, self.html)

    def test_admin_update_organisation_with_the_same_subscriptions(self):
        """
        Test admin update organisation and keep its subscriptions
        the same (/admin/organisation/edit).
        """
        url = "/admin/organisation/edit/?id=%d"
        organisation = self.fx.OrganisationData.pmg
        self.create_organisation_data["subscriptions"] = self.fx.CommitteeData.arts.id
        response = self.make_request(
            url % organisation.id,
            self.user,
            data=self.create_organisation_data,
            method="POST",
            follow_redirects=True,
        )

    def test_admin_update_organisation_with_new_subscriptions(self):
        """
        Test admin update organisation with new subscriptions 
        (/admin/organisation/edit).
        """
        url = "/admin/organisation/edit/?id=%d"
        organisation = self.fx.OrganisationData.pmg
        self.create_organisation_data[
            "subscriptions"
        ] = self.fx.CommitteeData.communications.id
        response = self.make_request(
            url % organisation.id,
            self.user,
            data=self.create_organisation_data,
            method="POST",
            follow_redirects=True,
        )
