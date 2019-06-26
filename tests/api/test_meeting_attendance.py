from tests import PMGTestCase
from tests.fixtures import (dbfixture, CommitteeMeetingAttendanceData,
                            PartyData, ProvinceData, MemberData, CommitteeData,
                            HouseData)


class TestCommitteeMeetingAttendance(PMGTestCase):
    def setUp(self):
        super(TestCommitteeMeetingAttendance, self).setUp()
        self.fx = dbfixture.data(PartyData, ProvinceData, HouseData,
                                 MemberData, CommitteeData,
                                 CommitteeMeetingAttendanceData)
        self.fx.setup()

    def test_member_attendance_count(self):
        res = self.client.get(
            'committee-meeting-attendance/',
            base_url='http://api.pmg.test:5000/')
        self.assertEqual(200, res.status_code)
        self.assertEqual(8, res.json.get('count'))

    def test_committee_page(self):
        res = self.client.get(
            'committee/%s/' % self.fx.CommitteeData.arts.id,
            base_url='http://pmg.test:5000/')
        self.assert_template_used('committee_detail.html')
        self.assertEqual(200, res.status_code)
