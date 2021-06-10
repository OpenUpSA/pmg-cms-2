from builtins import str
from tests import PMGLiveServerTestCase
from pmg.models import db, Member
from tests.fixtures import dbfixture, MemberData, UserData, MembershipData


class TestAdminMemberPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminMemberPage, self).setUp()

        self.fx = dbfixture.data(UserData, MemberData, MembershipData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminMemberPage, self).tearDown()

    def test_view_admin_member_page(self):
        """
        Test view admin member page (/admin/member)
        """
        self.make_request("/admin/member", self.user, follow_redirects=True)
        self.assertIn("Members", self.html)
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
        Create a member with the admin interface (/admin/member/new/)
        """
        before_count = len(Member.query.all())
        url = "/admin/member/new/?url=%2Fadmin%2Fmember%2F"
        data = {
            "name": "New member",
            "current": "y",
            "monitored": "y",
            "house": "__None",
            "party": "__None",
            "province": "__None",
            "bio": "",
            "pa_link": "",
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Member.query.all())
        self.assertEqual(302, response.status_code)
        self.assertLess(before_count, after_count)

        created_member = Member.query.filter(Member.name == data["name"]).scalar()
        self.assertTrue(created_member)
        self.created_objects.append(created_member)

    def test_admin_delete_member(self):
        """
        Delete a member with the admin interface (/admin/member/action/)
        """
        before_count = len(Member.query.all())
        url = "/admin/member/action/"
        data = {
            "url": "/admin/member/",
            "action": "delete",
            "rowid": [str(self.fx.MemberData.veronica.id),],
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Member.query.all())
        self.assertEqual(302, response.status_code)
        self.assertGreater(before_count, after_count)

    def test_admin_member_committee_meeting_attendance(self):
        """
        Lists member committee meeting attendance
        """

        attendance_url = "/admin/member/attendance/"
        member_id = '?id={}'.format(str(self.fx.MemberData.veronica.id))
        rest_of_url = "&url=%2Fadmin%2Fmember%2F"
        url = '{}{}{}'.format(attendance_url, member_id, rest_of_url)

        response = self.make_request(url, self.user, method="GET")
        self.assertEqual(200, response.status_code)
        self.assertIn('Attendance', self.html)
        self.assertIn('Attendance code', self.html)
        self.assertIn('Public meeting 2020 one"', self.html)
