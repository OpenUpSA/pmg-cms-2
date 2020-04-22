from tests import PMGTestCase
import datetime
import pytz
from pmg.models import db, CommitteeMeeting, Event, EventFile, File, House, Committee
from tests.fixtures import dbfixture, CommitteeData, CommitteeMeetingData, EventData


# TODO: might have to mock S3
class TestFiles(PMGTestCase):
    def setUp(self):
        super().setUp()
        self.house = House(name="National Assembly", name_short="NA", sphere="national")
        self.committee = Committee(
            name="Communications", house=self.house, premium=True
        )
        self.committee_meeting = CommitteeMeeting(
            date=datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
            title="Public meeting One",
            committee=self.committee,
        )
        self.file = File(file_path="test-path.pdf")
        self.event_file = EventFile(event=self.committee_meeting, file=self.file)
        db.session.add(self.house)
        db.session.add(self.committee)
        db.session.add(self.committee_meeting)
        db.session.add(self.event_file)
        db.session.commit()
        self.file_id = self.file.id

    def test_delete_file_when_linked_to_meeting(self):
        # When we delete the file, the event should be deleted too, but
        # the meeting shouldn't be deleted
        db.session.delete(self.file)
        db.session.commit()
        event_file = EventFile.query.filter_by(file_id=self.file_id).first()
        self.assertIsNone(event_file)
        committee_meeting = CommitteeMeeting.query.filter_by(
            id=self.committee_meeting.id
        ).first()
        self.assertIsNotNone(committee_meeting)
