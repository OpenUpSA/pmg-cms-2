from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, CommitteeMeetingData
import urllib2


class TestCommittees(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommittees, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommittees, self).tearDown()

    def test_committees_page(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committees"
        )
        html = res.read()
        self.assertEqual(200, res.code)
        self.assertIn('committees', html)
        self.assertIn(self.fx.CommitteeData.communications.name, html)
        self.assertIn(self.fx.CommitteeData.arts.name, html)
        self.assertIn(self.fx.CommitteeData.constitutional_review.name, html)

    def test_committee_page(self):
        res = urllib2.urlopen(
            "http://pmg.test:5000/committee/%s/"
            % self.fx.CommitteeData.communications.id
        )
        html = res.read()
        self.assertEqual(200, res.code)
        self.assertIn(str(self.fx.CommitteeData.communications.id), html)
