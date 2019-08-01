from tests import PMGLiveServerTestCase
from pmg.models import db
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
        self.fx.teardown()
        super(TestAdminCommitteePage, self).tearDown()

    def test_view_admin_committee_page(self):
        """
        Test view admin committee page (http://pmg.test:5000/admin/committee)
        """
        self.get_page_contents_as_user(
            self.user, "http://pmg.test:5000/admin/committee")
        self.assertIn('Committees', self.html)
        self.containsCommittee(self.fx.CommitteeData.communications)
        self.containsCommittee(self.fx.CommitteeData.arts)
        self.containsCommittee(self.fx.CommitteeData.constitutional_review)

    def containsCommittee(self, committee):
        self.assertIn(committee.name, self.html)
        self.assertIn(committee.house.name, self.html)
        self.assertIn(str(len(committee.memberships)), self.html)
