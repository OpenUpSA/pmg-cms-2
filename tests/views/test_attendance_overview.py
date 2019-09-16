from tests import PMGLiveServerTestCase
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
        db.session.commit()

    def test_attendance_overview(self):
        self.make_request("/attendance-overview")
        self.assertIn("Committee meeting attendance trends for 2019", self.html)
        self.assertIn("Arts and Culture", self.html)
        self.assertIn("50%", self.html)
        self.assertIn('<td class="number-meetings hidden-xs">1</td>', self.html)
        self.assertNotIn("Since", self.html)
