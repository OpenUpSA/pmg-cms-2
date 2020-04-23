from tests import PMGTestCase
import datetime
import pytz
from mock import patch
from pmg.models import db, CommitteeMeeting, Event, EventFile, File, House, Committee
from tests.fixtures import dbfixture, CommitteeData, CommitteeMeetingData, EventData


class MockS3Key:
    def delete():
        return True


class MockS3Bucket:
    def get_key(*args, **kwargs):
        return MockS3Key()


class MockS3:
    bucket = MockS3Bucket()

    def upload_file(*args, **kwargs):
        return True

    def delete():
        return True


class TestFiles(PMGTestCase):
    def setUp(self):
        super().setUp()
        self.house = House(name="Test House", name_short="TH", sphere="national")
        self.committee = Committee(
            name="Test Committee", house=self.house, premium=True
        )
        self.committee_meeting = CommitteeMeeting(
            date=datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
            title="Test meeting",
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

    @patch("pmg.models.resources.s3_bucket", return_value=MockS3())
    def test_delete_file_when_linked_to_meeting(self, mock_s3_bucket_key):
        # When we delete the file, the event_file many-to-many join table entries for the file 
        # should also be deleted but the meeting (event) should not be deleted
        db.session.delete(self.file)
        db.session.commit()
        event_file = EventFile.query.filter_by(file_id=self.file_id).first()
        self.assertIsNone(event_file)
        committee_meeting = CommitteeMeeting.query.filter_by(
            id=self.committee_meeting.id
        ).first()
        self.assertIsNotNone(committee_meeting)
