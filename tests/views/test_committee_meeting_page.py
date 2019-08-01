from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, CommitteeMeetingData
import urllib2


class TestCommitteeMeetingPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteeMeetingPage, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, CommitteeMeetingData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteeMeetingPage, self).tearDown()

    def test_premium_committee_meeting(self):
        """
        Test premium committee meeting page (http://pmg.test:5000/committee-meeting/<id>/)
        """
        meeting = self.fx.CommitteeMeetingData.premium_recent
        self.get_page_contents(
            "http://pmg.test:5000/committee-meeting/%s/"
            % meeting.id
        )
        self.assertIn(meeting.title, self.html)
        self.assertIn('Follow this committee', self.html)