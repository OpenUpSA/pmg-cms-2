from datetime import datetime
from pmg import db, app
from pmg.models import File
from soundcloud import Client
from sqlalchemy import desc, func
from sqlalchemy.orm import backref
import logging

logger = logging.getLogger(__name__)

SOUNDCLOUD_ARTWORK_PATH = 'pmg/static/resources/images/logo-artwork.png'


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
        if not file.event_files:
            logging.info("Skipping SoundCloud upload for file without events: %s" % file)
            return

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

        with file.open() as file_handle:
            logging.info("Uploading to SoundCloud: %s" % file)
            track = client.post('/tracks', track={
                'title': file.title,
                'description': cls._html_description(file),
                'sharing': 'public',
                'asset_data': file_handle,
                'license': 'cc-by',
                'artwork_data': open(SOUNDCLOUD_ARTWORK_PATH, 'rb'),
                'genre': file.event_files[0].event.type,
                'tag_list': file.event_files[0].event.type,
                'downloadable': 'true',
                'streamable': 'true',
                'feedable': 'true',
            })
            logging.info("Done uploading to SoundCloud: %s" % file)
            file_handle.close()

            soundcloud_track.uri = track.uri
            soundcloud_track.state = track.state
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

    @classmethod
    def get_unstarted_query(cls):
        """
        Get audio files for which there's no SoundcloudTrack.
        Order by id as a hacky way to roughly get the latest files first
        """
        return db.session.query(File) \
                         .outerjoin(cls) \
                         .filter(cls.file_id == None) \
                         .filter(File.file_mime.like('audio/%')) \
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
                           .filter(cls.state == 'processing') \
                           .order_by(cls.created_at).all()
        for track in tracks:
            track.sync_state(client)
