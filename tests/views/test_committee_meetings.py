from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, CommitteeMeetingData
import urllib2


class TestCommitteeMeetings(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteeMeetings, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, CommitteeMeetingData)
        self.fx.setup()

    def test_premium_committee_meeting(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committee-meeting/%s/"
            % self.fx.CommitteeMeetingData.premium_recent.id
        )
        self.assertEqual(200, res.code)
        self.assertTrue(False)
