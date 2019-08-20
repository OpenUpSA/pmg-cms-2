from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, MemberData
)


class TestMemberPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestMemberPage, self).setUp()

        self.fx = dbfixture.data(
            MemberData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestMemberPage, self).tearDown()

    def test_members_page(self):
        """
        Test members page (/members)
        """
        committee = self.fx.MemberData.veronica
        self.make_request("/members/")
        self.assertIn('Members of Parliament', self.html)
        self.assertIn('Search for members', self.html)

        self.check_member(MemberData.veronica)
        self.check_member(MemberData.not_current_member)
        self.check_member(MemberData.laetitia)

    def check_member(self, member):
        if member.current:
            self.contains_member(member)
        else:
            self.does_not_contain_member(member)

    def does_not_contain_member(self, member):
        self.assertNotIn(member.name, self.html)

    def contains_member(self, member):
        self.assertIn(member.name, self.html)
        if hasattr(member, 'profile_pic_url'):
            self.assertIn(member.profile_pic_url, self.html)
        else:
            self.assertIn('/static/resources/images/no-profile-pic.svg', self.html)

        self.assertIn(member.party.name, self.html)
        self.assertIn(member.house.name, self.html)
