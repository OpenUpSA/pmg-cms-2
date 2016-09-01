import logging
from pmg import db
from pmg.models import *
from pmg.models.soundcloud import SoundcloudTrack
from sqlalchemy import desc
import soundcloud

logger = logging.getLogger(__name__)


def get_unstarted_query():
    return db.session.query(File) \
                     .outerjoin(SoundcloudTrack) \
                     .filter(SoundcloudTrack.file_id == None) \
                     .filter(File.file_mime.like('audio/%')) \
                     .order_by(desc(File.id))


def get_unstarted_count(q):
    return q.count()


def get_unstarted_batch(q):
    return q.limit(app.config['MAX_SOUNDCLOUD_BATCH']).all()


def sync():
    client = soundcloud.Client(client_id=app.config['SOUNDCLOUD_APP_KEY_ID'],
                               client_secret=app.config['SOUNDCLOUD_APP_KEY_SECRET'],
                               username=app.config['SOUNDCLOUD_USERNAME'],
                               password=app.config['SOUNDCLOUD_PASSWORD'])
    sync_upload_state(client)
    upload_files(client)
    sync_upload_state(client)


def sync_upload_state(client):
    tracks = db.session.query(SoundcloudTrack) \
                       .filter(SoundcloudTrack.state == 'processing') \
                       .order_by(SoundcloudTrack.created_at).all()
    for track in tracks:
        soundcloud_track = client.get(track.uri)
        if soundcloud_track.state != track.state:
            track.state = soundcloud_track.state
            logger.info("SoundCloud track %s state is now [%s]" % (track, track.state))
        db.session.commit()


def upload_files(client):
    q = get_unstarted_query()
    logging.info("Audio files yet to be uploaded to SoundCloud: %d" % get_unstarted_count(q))
    batch = get_unstarted_batch(q)
    logging.info("Uploading %d files to SoundCloud" % len(batch))
    for file in batch:
        upload_file(client, file)


def upload_file(client, file):
    with file.open() as file_handle:
        logging.info("Uploading to SoundCloud: %s" % file)
        track = client.post('/tracks', track={
            'title': file.title,
            'description': description(file),
            'sharing': 'private',
            'asset_data': file_handle,
            'license': 'cc-by',
            'artwork_data': open('pmg/static/resources/images/logo-artwork.png', 'rb'),
            'genre': file.event_files[0].event.type,
            'tag_list': file.event_files[0].event.type,
            'downloadable': 'true',
            'streamable': 'true',
            'feedable': 'true',
        })
        logging.info("Done uploading to SoundCloud: %s" % file)
        file_handle.close()

    # Do a transaction per track to be as sure as we can that each
    # uploaded track is recorded on our side in case of unexpected errors.
    soundcloud_track = SoundcloudTrack(file, track)
    db.session.add(soundcloud_track)
    db.session.commit()


def description(file):
    return '<br>'.join("<a href='%s'>%s</a>" % (ef.event.url, ef.event.title)
                       for ef in file.event_files),
