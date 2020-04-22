from tests import PMGTestCase
import datetime
import pytz
from pmg.models import db, CommitteeMeeting, Event, EventFile, File, House, Committee
from tests.fixtures import dbfixture, CommitteeData, CommitteeMeetingData, EventData


# TODO: might have to mock S3
class TestFiles(PMGTestCase):
    def setUp(self):
        super().setUp()
        self.fx = dbfixture.data(CommitteeMeetingData)
        self.fx.setup()

        self.house = House(name="National Assembly", name_short="NA", sphere="national")

        committee_meeting_id = self.fx.CommitteeMeetingData.arts_meeting_one.id
        self.committee_meeting = CommitteeMeeting.query.filter_by(
            id=committee_meeting_id
        ).first()
        self.file = File(file_path="test-path.pdf")
        self.event_file = EventFile(event=self.committee_meeting, file=self.file)
        db.session.add(self.event_file)
        db.session.commit()

    def test_delete_file_when_linked_to_meeting(self):
        # WHEN we delete the file
        db.session.delete(self.file)
        db.session.commit()

        # THEN the event should be deleted too
        event_file = EventFile.query.filter_by(file_id=self.file.id).first()
        self.assertIsNone(event_file)

        # THEN the meeting should still exist
        committee_meeting = CommitteeMeeting.query.filter_by(
            id=self.committee_meeting.id
        ).first()
        self.assertIsNotNone(committee_meeting)
