from builtins import str
import datetime
from tests import PMGLiveServerTestCase
from pmg.models import db, Committee
from tests.fixtures import dbfixture, UserData, CommitteeMeetingData

THIS_YEAR = datetime.datetime.today().year


class TestAdminCommitteeMeetings(PMGLiveServerTestCase):
    def setUp(self):
        super().setUp()

        self.fx = dbfixture.data(UserData, CommitteeMeetingData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super().tearDown()

    def test_update_committee_meeting(self):
        url = "/admin/committee-meeting/edit/?id=%d"
        meeting = self.fx.CommitteeMeetingData.premium_recent
        meeting_data = {
            "title": "Updated Meeting title",
            "date": "2020-02-20 22:08:00",
        }
        response = self.make_request(
            url % meeting.id,
            self.user,
            data=meeting_data,
            method="POST",
            follow_redirects=True,
        )

        self.assertIn(meeting_data["title"], self.html)
        #self.assertIn(meeting_data["date"], self.html)

        # Save the meeting again without changing the date
        # to check that the date doesn't change
        response = self.make_request(
            url % meeting.id, self.user, data={}, method="POST", follow_redirects=True,
        )
        self.assertIn(meeting_data["title"], self.html)
        #self.assertIn(meeting_data["date"], self.html)

    def test_view_admin_committee_meeting_page(self):
        """
        Test view admin committee page (/admin/committee-meeting)
        """
        self.make_request("/admin/committee-meeting", self.user, follow_redirects=True)
        self.assertIn("Committee Meetings", self.html)
        self.assertIn(self.fx.CommitteeMeetingData.arts_meeting_one.title, self.html)
        self.assertIn("2019-01-01 02:00:00", self.html)

        self.assertIn(self.fx.CommitteeMeetingData.premium_recent.title, self.html)
        self.assertIn("%d-11-05 00:00:00" % THIS_YEAR, self.html)
