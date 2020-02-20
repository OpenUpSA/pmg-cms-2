from tests import PMGTestCase
from tests.fixtures import dbfixture, CommitteeMeetingData


class TestCommitteeMeetingAttendanceExcelExport(PMGTestCase):
    def setUp(self):
        super(TestCommitteeMeetingAttendanceExcelExport, self).setUp()

        self.fx = dbfixture.data(CommitteeMeetingData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteeMeetingAttendanceExcelExport, self).tearDown()

    def test_get_committee_meeting_attendance_xlsx_smoke_test(self):
        res = self.client.get(
            "committee-meeting-attendance/data.xlsx",
            base_url="http://api.pmg.test:5000/",
        )
        self.assertEqual(200, res.status_code)
