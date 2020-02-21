from nose.tools import *  # noqa
import datetime
from unittest.mock import MagicMock, patch, mock_open
from soundcloud import Client

from pmg.models.soundcloud_track import SoundcloudTrack
from pmg.models import db, File, Event, EventFile
from tests import PMGTestCase
from requests.exceptions import HTTPError


class TestSoundcloudTrack(PMGTestCase):
    def setUp(self):
        super(TestSoundcloudTrack, self).setUp()
        self.create_audio_file()
        self.create_soundtrack_file()

    def create_audio_file(self):
        self.event = Event(
            date=datetime.datetime.today(),
            title="Test event",
            type="committee-meeting",
        )
        self.file = File(
            title="Test Audio",
            file_mime="audio/mp3",
            file_path="tmp/file",
            file_bytes="1",
            origname="Test file",
            description="Test file",
            playtime="3min",
        )
        self.event_file = EventFile(event=self.event, file=self.file)
        db.session.add(self.event)
        db.session.add(self.file)
        db.session.add(self.event_file)
        db.session.commit()

    def create_soundtrack_file(self):
        self.uploaded_file = File(
            title="Test Audio",
            file_mime="audio/mp3",
            file_path="tmp/file-2",
            file_bytes="1",
            origname="Test file 2",
            description="Test file 2",
            playtime="3min",
        )
        self.soundcloud_track = SoundcloudTrack(
            file=self.uploaded_file,
            uri="https://soundcloud.com/pmgza/test-file",
            state="processing",
        )
        db.session.add(self.uploaded_file)
        db.session.add(self.soundcloud_track)
        db.session.commit()

    def test_get_unstarted_query(self):
        query = SoundcloudTrack.get_unstarted_query()
        self.assertEquals(1, query.count())
        self.assertIn(self.file, query.all())
        self.assertEquals(SoundcloudTrack.get_unstarted_count(query), 1)

    @patch(
        "pmg.models.soundcloud_track.Client",
        side_effect=HTTPError(
            "500 Server Error: Internal Server Error for url: https://api.soundcloud.com/tracks/345302324?oauth_token=1-265188-164&client_id=43b75"
        ),
    )
    def test_sync_with_500_error(self, mock_client):
        client_mock = MagicMock()
        track_mock = MagicMock()
        track_mock.state = "processing"
        client_mock.get.return_value = track_mock
        self.assertRaises(HTTPError, SoundcloudTrack.sync)

    def test_sync_upload_state(self):
        client_mock = MagicMock()
        track_mock = MagicMock()
        track_mock.state = "processing"
        client_mock.get.return_value = track_mock
        SoundcloudTrack.sync_upload_state(client_mock)
        client_mock.get.assert_called_with(self.soundcloud_track.uri)

    def test_new_from_file_already_being_uploaded(self):
        client_mock = MagicMock()

        self.soundcloud_track = SoundcloudTrack(
            file=self.file,
            uri="https://soundcloud.com/pmgza/test-file-2",
            state="processing",
        )
        db.session.commit()

        soundcloud_file_count_before = SoundcloudTrack.query.count()
        SoundcloudTrack.new_from_file(client_mock, self.file)
        soundcloud_file_count_after = SoundcloudTrack.query.count()
        self.assertEqual(soundcloud_file_count_before, soundcloud_file_count_after)
