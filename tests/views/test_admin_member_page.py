from tests import PMGLiveServerTestCase
from pmg.models import db
from tests.fixtures import (
    dbfixture, MemberData, UserData, MembershipData
)


class TestAdminMemberPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminMemberPage, self).setUp()

        self.fx = dbfixture.data(
            UserData, MemberData, MembershipData
        )
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.fx.teardown()
        super(TestAdminMemberPage, self).tearDown()

    def test_view_admin_member_page(self):
        """
        Test view admin member page (http://pmg.test:5000/admin/member)
        """
        self.get_page_contents_as_user(
            self.user, "http://pmg.test:5000/admin/member")
        self.assertIn('Members', self.html)
        self.containsMember(self.fx.MemberData.veronica)
        self.containsMember(self.fx.MemberData.laetitia)
        self.containsMember(self.fx.MemberData.not_current_member)

    def containsMember(self, member):
        self.assertIn(member.name, self.html)
        if member.house:
            self.assertIn(member.house.name, self.html)
        if member.party:
            self.assertIn(member.party.name, self.html)
        if member.province:
            self.assertIn(member.province.name, self.html)
        if member.profile_pic_url:
            self.assertIn(member.profile_pic_url, self.html)
        for membership in member.memberships:
            self.assertIn(membership.committee.name, self.html)
