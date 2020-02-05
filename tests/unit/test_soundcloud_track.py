from nose.tools import *  # noqa
import datetime

from pmg.models.soundcloud_track import SoundcloudTrack
from pmg.models import db, File, Event, EventFile
from tests import PMGTestCase


class TestUser(PMGTestCase):
    def test_get_unstarted_query(self):
        event = Event(
            date=datetime.datetime.today(),
            title="Test event",
            type="committee-meeting",
        )
        file = File(
            title="Test Audio",
            file_mime="audio/mp3",
            file_path="tmp/file",
            file_bytes="1",
            origname="Test file",
            description="Test file",
            playtime="3min",
            # event_files=db.relationship("EventFile", lazy=True),
        )
        event_file = EventFile(
            event=event,
            file=file
        )
        db.session.add(event)
        db.session.add(file)
        db.session.add(event_file)
        db.session.commit()
        query = SoundcloudTrack.get_unstarted_query()
        self.assertEquals(1, query.count())
        self.assertIn(file, query.all())
