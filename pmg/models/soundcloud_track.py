from datetime import datetime
from pmg import db, app
from pmg.models import File, EventFile
from requests.exceptions import HTTPError
from soundcloud import Client
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import backref
import logging

logger = logging.getLogger(__name__)

SOUNDCLOUD_ARTWORK_PATH = 'pmg/static/resources/images/logo-artwork.png'
UNFINISHED_STATES = [
    'storing',
    'stored',
    'processing',
]


class SoundcloudTrack(db.Model):
    """
    - Tracks where uri and state is null are either busy being uploaded,
      or failed to upload to SoundCloud.
    - Tracks where state is 'failed' reflect that soundcloud
      failed to process the track.
    """
    __tablename__ = "soundcloud_track"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=func.current_timestamp()
    )
    file_id = db.Column(
        db.Integer,
        db.ForeignKey('file.id'),
        nullable=False,
        unique=True
    )
    file = db.relationship('File', backref=backref('soundcloud_track', uselist=False, lazy='joined'), lazy=True)
    # Soundcloud resource URI for the track (i.e. https://api.soundcloud...id)
    uri = db.Column(db.String())
    # Last known value of SoundCloud's opinion of the track state
    state = db.Column(db.String())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'<SoundcloudTrack id=%d>' % self.id

    @classmethod
    def new_from_file(cls, client, file):
        if db.session.query(cls.id).filter(cls.file_id == file.id).scalar() is not None:
            logging.info("File already started being uploaded to Soundcloud: %s" % file)
            db.session.rollback()
            return
        # Immediately create the SoundcloudTrack to indicate that work
        # has started for this track and may be in progress.
        # Potential concurrent runs can rely on an exception here to avoid
        # uploading the same file twice.
        soundcloud_track = cls(file=file)
        db.session.add(soundcloud_track)
        db.session.commit()
        soundcloud_track._upload(client)

    def _upload(self, client):
        with self.file.open() as file_handle:
            logging.info("Uploading to SoundCloud: %s" % self.file)
            track = client.post('/tracks', track={
                'title': self.file.title,
                'description': SoundcloudTrack._html_description(self.file),
                'sharing': 'public',
                'asset_data': file_handle,
                'license': 'cc-by',
                'artwork_data': open(SOUNDCLOUD_ARTWORK_PATH, 'rb'),
                'genre': self.file.event_files[0].event.type,
                'tag_list': self.file.event_files[0].event.type,
                'downloadable': 'true',
                'streamable': 'true',
                'feedable': 'true',
            })
            logging.info("Done uploading to SoundCloud: %s" % self.file)
            file_handle.close()

            self.uri = track.uri
            self.state = track.state
            db.session.commit()


    @staticmethod
    def _html_description(file):
        """
        HTML description for presentation on Soundcloud.
        staticmethod because it's needed before the instance exists.
        """
        return 'Sound recording from:<br>' + \
            '<br>'.join(
                "<a href='%s'>%s</a>" % (ef.event.url, ef.event.title)
                for ef in file.event_files
            )

    def sync_state(self, client):
        track = client.get(self.uri)
        if track.state != self.state:
            self.state = track.state
            db.session.commit()
            logger.info("SoundCloud track %s state is now [%s]" % (self, self.state))

    @classmethod
    def upload_files(cls, client):
        q = cls.get_unstarted_query()
        logging.info("Audio files yet to be uploaded to SoundCloud: %d"
                     % cls.get_unstarted_count(q))
        batch = cls.get_unstarted_batch(q)
        # Rollback this transaction - it was just to gather candidates for upload
        db.session.rollback()
        logging.info("Uploading %d files to SoundCloud" % len(batch))
        for file in batch:
            cls.new_from_file(client, file)

    @classmethod
    def sync(cls):
        client = Client(client_id=app.config['SOUNDCLOUD_APP_KEY_ID'],
                        client_secret=app.config['SOUNDCLOUD_APP_KEY_SECRET'],
                        username=app.config['SOUNDCLOUD_USERNAME'],
                        password=app.config['SOUNDCLOUD_PASSWORD'])
        cls.upload_files(client)
        cls.sync_upload_state(client)
        cls.handle_failed(client)

    @classmethod
    def get_unstarted_query(cls):
        """
        Get audio files for which there's no SoundcloudTrack.
        Order by id as a hacky way to roughly get the latest files first
        """
        # Query files that aren't connected to events so we can ignore them for
        # now - it's not clear that they're actually visible - they might well
        # have been mistaken uploads that shouldn't suddenly appear on PMG's
        # public soundcloud profile.
        q_files_with_meetings = db.session.query(File.id) \
                                          .outerjoin(EventFile) \
                                          .filter(EventFile.file_id == None) \
                                          .filter(File.file_mime.like('audio/%'))
        return db.session.query(File) \
                         .outerjoin(cls) \
                         .filter(cls.file_id == None) \
                         .filter(File.file_mime.like('audio/%')) \
                         .filter(~File.id.in_(q_files_with_meetings)) \
                         .order_by(desc(File.id))

    @staticmethod
    def get_unstarted_count(q):
        return q.count()

    @staticmethod
    def get_unstarted_batch(q):
        return q.limit(app.config['MAX_SOUNDCLOUD_BATCH']).all()

    @classmethod
    def sync_upload_state(cls, client):
        tracks = db.session.query(cls) \
                           .filter(cls.state.in_(UNFINISHED_STATES)) \
                           .order_by(cls.created_at).all()
        for track in tracks:
            track.sync_state(client)

    @classmethod
    def handle_failed(cls, client):
        for track_id, retries in db.session.query(cls.id,
                                                  func.count(SoundcloudTrackRetry.id).label('retries'))\
                                           .filter(cls.state == 'failed')\
                                           .outerjoin(SoundcloudTrackRetry)\
                                           .group_by(cls.id)\
                                           .order_by('retries')\
                                           .limit(app.config['MAX_SOUNDCLOUD_BATCH']):
            if retries <= app.config['MAX_SOUNDCLOUD_RETRIES']:
                soundcloud_track = db.session.query(cls).get(track_id)
                # Sometimes tracks apparently go from failed to finished. Yeah.
                soundcloud_track.sync_state(client)
                if soundcloud_track.state == 'failed':
                    soundcloud_track.retry_upload(client)

    def retry_upload(self, client):
        logging.info("Retrying failed soundcloud track %r" % self)
        retry = SoundcloudTrackRetry(soundcloud_track=self)
        db.session.add(retry)
        db.session.commit()
        try:
            client.delete(self.uri)
        except HTTPError as delete_result:
            # Handle brokenness at SoundCloud where deleting a track
            # results with an HTTP 500 response yet the track
            # is gone (HTTP 404) when you try to GET it.
            if delete_result.response.status_code == 500:
                try:
                    client.get(self.uri)
                    # If the delete gves a 500 and the GET doesn't
                    # give a 404, something bad happened.
                    raise Exception("Tried to delete but track %s still there" % self.uri)
                except HTTPError as get_result:
                    if get_result.response.status_code != 404:
                        raise Exception("Can't tell if track %s that we attempted " +\
                                        "to delete is still there." % self.uri)
            elif delete_result.response.status_code == 404:
                logging.info("Track %s was already missing from SoundCloud when " +\
                             "to retry %r" % (self.uri, self))
            elif delete_result.response.status_code != 200:
                raise Exception("Unexpected result when deleting %s from " +\
                                "SoundCloud" % self)
        # If we get here we expect that we've successfully deleted
        # the failed track from SoundCloud.
        # Indicate that we've started uploading
        self.state = None
        db.session.commit()
        self._upload(client)


class SoundcloudTrackRetry(db.Model):
    __tablename__ = "soundcloud_track_retry"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=func.current_timestamp()
    )
    soundcloud_track_id = db.Column(
        db.Integer,
        db.ForeignKey('soundcloud_track.id'),
        nullable=False,
        unique=False
    )
    soundcloud_track = db.relationship('SoundcloudTrack', backref=backref('retries', lazy='joined'), lazy=True)
