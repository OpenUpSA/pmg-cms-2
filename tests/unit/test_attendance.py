from tests import PMGTestCase
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


class TestCommitteeMeetingAttendance(PMGTestCase):
    def setUp(self):
        super(TestCommitteeMeetingAttendance, self).setUp()
        province = Province(name="Western Cape")
        db.session.add(province)
        party = Party(name="Global Party")
        db.session.add(party)
        house = House(name="National Assembly", sphere="national", name_short="na")
        db.session.add(house)
        db.session.commit()

        self.committee = committee = Committee(name="Arts and Culture", house=house)
        db.session.add(committee)
        db.session.commit()

        old_parliament_meeting = CommitteeMeeting(
            title="Jan Arts 1", date="2019-01-01", committee=committee
        )
        db.session.add(old_parliament_meeting)
        old_parliament_meeting_two = CommitteeMeeting(
            title="Feb Arts 2", date="2019-02-01", committee=committee
        )
        db.session.add(old_parliament_meeting_two)

        new_parliament_meeting = CommitteeMeeting(
            title="Arts 2", date="2019-06-01", committee=committee
        )
        db.session.add(new_parliament_meeting)

        future_parliament_meeting_one = CommitteeMeeting(
            title="Arts 2020", date="2020-02-01", committee=committee
        )
        future_parliament_meeting_two = CommitteeMeeting(
            title="Arts 2020", date="2020-07-01", committee=committee
        )
        db.session.add(future_parliament_meeting_one)
        db.session.add(future_parliament_meeting_two)

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
            created_at="2019-08-01",
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
        attendance_three_mike = CommitteeMeetingAttendance(
            attendance="A",
            member=mike,
            meeting=future_parliament_meeting_one,
            created_at="2020-08-01",
        )
        attendance_four_mike = CommitteeMeetingAttendance(
            attendance="P",
            member=mike,
            meeting=future_parliament_meeting_two,
            created_at="2020-08-01",
        )
        db.session.add(attendance_three_mike)
        db.session.add(attendance_four_mike)
        db.session.commit()

    def test_committee_attendance_trends(self):
        """
        new data will show up on the page requesting "current" and NOT on "historical
        old data will show up on the page requesting "historical" and NOT on "current"
        """
        committee = Committee.query.filter_by(name="Arts and Culture").first()
        current_attendance = CommitteeMeetingAttendance.committee_attendence_trends(
            committee.id, "current"
        )
        historical_attendance = CommitteeMeetingAttendance.committee_attendence_trends(
            committee.id, "historical"
        )

        self.assertEqual([], current_attendance)
        self.assertEqual(
            [(2019.0, 3, 0.5, 2.0), (2020.0, 2, 0.5, 1.0)], historical_attendance
        )

    def test_committee_attendance_summary(self):
        """
        checking that the correct number of rows are returned from a attendance summary
        """
        current_attendance = CommitteeMeetingAttendance.summary()
        historical_attendance = CommitteeMeetingAttendance.summary("historical")
        self.assertEqual(
            [],
            current_attendance,
        )
        self.assertEqual(
            [
                (2, "A", 2020.0, 1, 1),
                (2, "P", 2020.0, 1, 1),
                (1, "A", 2019.0, 1, 1),
                (1, "P", 2019.0, 1, 2),
                (2, "A", 2019.0, 1, 2),
                (2, "P", 2019.0, 1, 1),
            ],
            historical_attendance,
        )

    def test_annual_attendance_trends(self):
        trends = CommitteeMeetingAttendance.annual_attendance_trends(to_year=2024)

        expected = []

        self.assertEqual(expected, trends)

    def test_annual_attendance_trends_historical(self):
        trends = CommitteeMeetingAttendance.annual_attendance_trends(
            to_year=2019, period="historical"
        )

        expected = []

        self.assertEqual(expected, trends)
