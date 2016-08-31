import logging
from pmg import db
from pmg.models import *
from pmg.models.soundcloud import SoundcloudTrack
from sqlalchemy import desc
import soundcloud

logger = logging.getLogger(__name__)


def get_unstarted_query():
    return db.session.query(File, Event.title.label('event_title')) \
                     .join(EventFile) \
                     .join(Event) \
                     .outerjoin(SoundcloudTrack) \
                     .filter(SoundcloudTrack.file_id == None) \
                     .filter(File.file_mime.like('audio/%')) \
                     .order_by(desc(Event.date))


def get_unstarted_count(q):
    return q.count()


def get_unstarted_batch(q):
    return q.limit(app.config['MAX_SOUNDCLOUD_BATCH']).all()


def sync():
    q = get_unstarted_query()
    logging.info("Audio files yet to be uploaded to SoundCloud: %d" % get_unstarted_count(q))
    batch = get_unstarted_batch(q)
    logging.info("Uploading %d files to SoundCloud" % get_unstarted_count(q))
    for file, event_title in batch:
        upload_file(file, event_title)


def upload_file(file, event_title):
    logging.info("Downloading from S3: %s" % file)
    file_handle = file.download()
    # create client object with app and user credentials
    client = soundcloud.Client(client_id=app.config['SOUNDCLOUD_APP_KEY_ID'],
                               client_secret=app.config['SOUNDCLOUD_APP_KEY_SECRET'],
                               username=app.config['SOUNDCLOUD_USERNAME'],
                               password=app.config['SOUNDCLOUD_PASSWORD'])

    logging.info("Uploading to SoundCloud: %s" % file)
    track = client.post('/tracks', track={
        'title': file.title,
        'description': event_title,
        'sharing': 'private',
        'asset_data': file_handle,
    })
    logging.info("Done Uploading to SoundCloud: %s" % file)
    file_handle.close()

    # Do a transaction per track to be as sure as we can that each
    # uploaded track is recorded on our side in case of unexpected errors.
    soundcloud_track = SoundcloudTrack(file, track)
    db.session.add(soundcloud_track)
    db.session.commit()
