from tests import PMGLiveServerTestCase
from mock import patch
from datetime import date
from pmg.models import (
    db,
    CommitteeMeeting,
    CommitteeMeetingAttendance,
    Committee,
    House,
    Province,
    Party,
    Member,
)

HISTORICAL_HEADING_FORMAT = "Historical Committee meeting attendance trends for %d"
HEADING_FORMAT = "Committee meeting attendance trends for %d"
NUM_MEETINGS_FORMAT = '<td class="number-meetings hidden-xs">%d</td>'
SINCE_FORMAT = "Since %d"
ATTENDANCE_FORMAT = '<td class="attendance" data-value="%s">'
CHANGE_FORMAT = '<td class="attendance-change" data-value="%s">'


class TestAttendanceOverview(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAttendanceOverview, self).setUp()

        province = Province(name="Western Cape")
        db.session.add(province)
        party = Party(name="Global Party")
        db.session.add(party)
        house = House(name="National Assembly", sphere="national", name_short="NA")
        db.session.add(house)
        db.session.commit()
        committee = Committee(name="Arts and Culture", house=house)
        db.session.add(committee)
        db.session.commit()
        old_parliament_meeting = CommitteeMeeting(
            title="Jan Arts 1", date="2019-01-01", committee=committee
        )
        db.session.add(old_parliament_meeting)
        old_parliament_meeting_two = CommitteeMeeting(
            title="Feb Arts 2", date="2019-05-31", committee=committee
        )
        db.session.add(old_parliament_meeting_two)
        new_parliament_meeting = CommitteeMeeting(
            title="Arts 2", date="2019-06-01", committee=committee
        )
        db.session.add(new_parliament_meeting)
        future_parliament_meeting_2020 = CommitteeMeeting(
            title="Arts 2", date="2020-06-01", committee=committee
        )
        future_parliament_meeting_2021 = CommitteeMeeting(
            title="Arts 2", date="2021-06-01", committee=committee
        )
        db.session.add(future_parliament_meeting_2020)
        db.session.add(future_parliament_meeting_2021)
        db.session.commit()

        jabu = Member(
            name="Jabu", current=True, party=party, house=house, province=province
        )
        mike = Member(
            name="Mike", current=True, party=party, house=house, province=province
        )
        db.session.add(jabu)
        db.session.add(mike)
        db.session.commit()

        attendance_one_jabu = CommitteeMeetingAttendance(
            attendance="P",
            member=jabu,
            meeting=old_parliament_meeting,
            created_at="2019-01-01",
        )
        db.session.add(attendance_one_jabu)
        attendance_one_mike = CommitteeMeetingAttendance(
            attendance="P",
            member=mike,
            meeting=old_parliament_meeting,
            created_at="2019-01-01",
        )
        db.session.add(attendance_one_mike)

        feb_attend_jabu = CommitteeMeetingAttendance(
            attendance="A",
            member=jabu,
            meeting=old_parliament_meeting_two,
            created_at="2019-02-01",
        )
        db.session.add(feb_attend_jabu)
        feb_attend_mike = CommitteeMeetingAttendance(
            attendance="A",
            member=mike,
            meeting=old_parliament_meeting_two,
            created_at="2019-02-01",
        )
        db.session.add(feb_attend_mike)

        attendance_two_jabu = CommitteeMeetingAttendance(
            attendance="P",
            member=jabu,
            meeting=new_parliament_meeting,
            created_at="2019-08-01",
        )
        db.session.add(attendance_two_jabu)
        attendance_two_mike = CommitteeMeetingAttendance(
            attendance="A",
            member=mike,
            meeting=new_parliament_meeting,
            created_at="2019-08-01",
        )
        db.session.add(attendance_two_mike)

        future_attendance_jabu_one = CommitteeMeetingAttendance(
            attendance="P",
            member=jabu,
            meeting=future_parliament_meeting_2020,
            created_at="2020-08-01",
        )
        db.session.add(future_attendance_jabu_one)
        future_attendance_mike_one = CommitteeMeetingAttendance(
            attendance="P",
            member=mike,
            meeting=future_parliament_meeting_2020,
            created_at="2020-08-01",
        )
        db.session.add(future_attendance_mike_one)
        future_attendance_jabu_2021 = CommitteeMeetingAttendance(
            attendance="P",
            member=jabu,
            meeting=future_parliament_meeting_2021,
            created_at="2021-08-01",
        )
        db.session.add(future_attendance_jabu_2021)
        future_attendance_mike_2021 = CommitteeMeetingAttendance(
            attendance="A",
            member=mike,
            meeting=future_parliament_meeting_2021,
            created_at="2021-08-01",
        )
        db.session.add(future_attendance_mike_2021)
        db.session.commit()

    @patch("pmg.views.datetime")
    def test_attendance_overview_2019(self, date_mock):
        date_mock.today.return_value = date(2019, 1, 1)
        self.make_request("/attendance-overview")
        self.assertIn(HEADING_FORMAT % 2019, self.html)
        self.assertNotIn("Since", self.html)

    @patch("pmg.views.datetime")
    def test_attendance_overview_for_no_attendance_data_2019(self, date_mock):
        date_mock.today.return_value = date(2019, 1, 1)
        CommitteeMeetingAttendance.query.delete()
        res = self.make_request("/attendance-overview")
        self.assertEqual(200, res.status_code)
        self.assertIn(HEADING_FORMAT % 2019, self.html)
        self.assertNotIn("Arts and Culture", self.html)

    @patch("pmg.views.datetime")
    def test_attendance_overview_2020(self, date_mock):
        date_mock.today.return_value = date(2020, 1, 1)
        self.make_request("/attendance-overview")
        self.assertIn(HEADING_FORMAT % 2020, self.html)

    @patch("pmg.views.datetime")
    def test_attendance_overview_2021(self, date_mock):
        date_mock.today.return_value = date(2021, 1, 1)
        self.make_request("/attendance-overview")
        self.assertIn(HEADING_FORMAT % 2021, self.html)
        self.assertIn("Attendance Methodology", self.html)

    def test_archived_attendance_overview(self):
        self.make_request("/archived-attendance-overview")
        self.assertIn(HEADING_FORMAT % 2019, self.html)
        self.assertIn("Attendance Methodology", self.html)

    def test_archived_attendance_overview_for_no_attendance_data(self):
        CommitteeMeetingAttendance.query.delete()
        res = self.make_request("/archived-attendance-overview")
        self.assertEqual(200, res.status_code)
        self.assertIn(HISTORICAL_HEADING_FORMAT % 2019, self.html)
        self.assertNotIn("Arts and Culture", self.html)
