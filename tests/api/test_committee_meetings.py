from tests import PMGTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, CommitteeMeetingData


class TestCommitteeMeetingsAPI(PMGTestCase):
    def setUp(self):
        super(TestCommitteeMeetingsAPI, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, CommitteeMeetingData)
        self.fx.setup()

    def test_premium_committee_meeting(self):
        res = self.client.get('/committee-meeting/%s/' % self.fx.CommitteeMeetingData.premium_recent.id, base_url='http://api.pmg.test:5000/')
        self.assertEqual(200, res.status_code)
        self.assertTrue(res.json['premium_content_excluded'])

    def test_premium_committee_meeting_old(self):
        res = self.client.get('/committee-meeting/%s/' % self.fx.CommitteeMeetingData.premium_old.id, base_url='http://api.pmg.test:5000/')
        self.assertEqual(200, res.status_code)
        self.assertIsNone(res.json.get('premium_content_excluded'))
