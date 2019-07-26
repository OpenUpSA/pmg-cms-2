from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, CommitteeMeetingData
import urllib2


class TestCommitteeMeetings(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteeMeetings, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, CommitteeMeetingData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteeMeetings, self).tearDown()

    def test_premium_committee_meeting(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committee-meeting/%s/"
            % self.fx.CommitteeMeetingData.premium_recent.id
        )
        self.assertEqual(200, res.code)
        self.assertTrue(False)

    def test_premium_committee_meeting3(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committee-meeting/%s/"
            % self.fx.CommitteeMeetingData.premium_recent.id
        )
        self.assertEqual(200, res.code)
        self.assertTrue(False)


class TestCommitteeMeetings2(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteeMeetings2, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, CommitteeMeetingData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteeMeetings2, self).tearDown()

    def test_premium_committee_meeting2(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committee-meeting/%s/"
            % self.fx.CommitteeMeetingData.premium_recent.id
        )
        self.assertEqual(200, res.code)
        self.assertTrue(False)
