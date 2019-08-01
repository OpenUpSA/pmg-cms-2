from tests import PMGLiveServerTestCase
from pmg.models import db, Member
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
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminMemberPage, self).tearDown()

    def test_view_admin_member_page(self):
        """
        Test view admin member page (http://pmg.test:5000/admin/member)
        """
        self.request_as_user(
            self.user, "http://pmg.test:5000/admin/member", follow_redirects=True)
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

    def test_admin_create_member(self):
        """
        Create a member with the admin interface (http://pmg.test:5000/admin/member/new/)
        """
        before_count = len(Member.query.all())
        url = "http://pmg.test:5000/admin/member/new/?url=%2Fadmin%2Fmember%2F"
        data = {
            'name': 'New member',
            'current': 'y',
            'monitored': 'y',
            'house': '__None',
            'party': '__None',
            'province': '__None',
            'bio': '',
            'pa_link': '',
        }
        response = self.request_as_user(
            self.user, url, data=data, method="POST")
        after_count = len(Member.query.all())
        self.assertEqual(302, response.status_code)
        self.assertLess(before_count, after_count)

        created_member = Member.query.filter(
            Member.name == data['name']).scalar()
        self.assertTrue(created_member)
        self.created_objects.append(created_member)
