from tests import PMGLiveServerTestCase
from pmg.models import db, Committee
from tests.fixtures import (
    dbfixture, UserData, CommitteeData, MembershipData
)


class TestAdminCommitteePage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminCommitteePage, self).setUp()

        self.fx = dbfixture.data(
            UserData, CommitteeData, MembershipData
        )
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminCommitteePage, self).tearDown()

    def test_view_admin_committee_page(self):
        """
        Test view admin committee page (/admin/committee)
        """
        self.make_request(
            "/admin/committee", self.user, follow_redirects=True)
        self.assertIn('Committees', self.html)
        self.containsCommittee(self.fx.CommitteeData.communications)
        self.containsCommittee(self.fx.CommitteeData.arts)
        self.containsCommittee(self.fx.CommitteeData.constitutional_review)

    def containsCommittee(self, committee):
        self.assertIn(committee.name, self.html)
        self.assertIn(committee.house.name, self.html)
        self.assertIn(str(len(committee.memberships)), self.html)

    def test_admin_create_committee(self):
        """
        Create a committee with the admin interface (/admin/committee/new/)
        """
        before_count = len(Committee.query.all())
        url = "/admin/committee/new/?url=%2Fadmin%2Fcommittee%2F"
        data = {
            'name': 'New committee',
            'active': 'y',
            'monitored': 'y',
            'house': str(self.fx.HouseData.na.id),
            'minister': '__None',
            'about': '',
            'contact_details': '',
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Committee.query.all())
        self.assertEqual(302, response.status_code)
        self.assertLess(before_count, after_count)

        created_committee = Committee.query.filter(Committee.name == data['name']).scalar()
        self.assertTrue(created_committee)
        self.created_objects.append(created_committee)

    def test_admin_delete_committee(self):
        """
        Delete a committee with the admin interface (/admin/committee/action/)
        """
        before_count = len(Committee.query.all())
        url = "/admin/committee/action/"
        data = {
            'url': '/admin/committee/',
            'action': 'delete',
            'rowid': [
                str(self.fx.CommitteeData.communications.id),
            ]
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Committee.query.all())
        self.assertEqual(302, response.status_code)
        self.assertGreater(before_count, after_count)
