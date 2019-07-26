from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, HouseData, CommitteeData, CommitteeMeetingData, CallForCommentData
)
import urllib2


class TestCommittees(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommittees, self).setUp()

        self.fx = dbfixture.data(
            HouseData, CommitteeData, CommitteeMeetingData, CallForCommentData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommittees, self).tearDown()

    def get_page_contents(self, url):
        res = urllib2.urlopen(url)
        self.assertEqual(200, res.code)
        return res.read()

    def test_committees_page(self):
        html = self.get_page_contents("http://pmg.test:5000/committees")
        self.assertIn('committees', html)
        self.assertIn(self.fx.CommitteeData.communications.name, html)
        self.assertIn(self.fx.CommitteeData.arts.name, html)
        self.assertIn(self.fx.CommitteeData.constitutional_review.name, html)
        self.assertIn(self.fx.HouseData.cjoint.name, html)

    def test_committee_page(self):
        committee = self.fx.CommitteeData.arts
        html = self.get_page_contents(
            "http://pmg.test:5000/committee/%s/"
            % committee.id
        )
        self.assertIn(committee.name, html)
        headings = ['Committee meetings', 'Calls for comment',
                    'Tabled reports', 'Questions and replies', 'Bills']
        for heading in headings:
            self.assertIn(heading, html)

    def test_committee_page_meetings(self):
        committee = self.fx.CommitteeData.arts
        html = self.get_page_contents(
            "http://pmg.test:5000/committee/%s/"
            % committee.id
        )

        self.assertIn(
            self.fx.CommitteeMeetingData.arts_meeting_one.title, html)
        self.assertIn(
            self.fx.CommitteeMeetingData.arts_meeting_two.title, html)

    def test_committee_calls_for_comment(self):
        committee = self.fx.CommitteeData.arts
        html = self.get_page_contents(
            "http://pmg.test:5000/committee/%s/"
            % committee.id
        )

        self.assertIn(self.fx.CallForCommentData.arts_call_for_comment_one, html)
