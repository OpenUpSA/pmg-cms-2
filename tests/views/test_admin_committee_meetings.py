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
