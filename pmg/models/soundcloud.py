from datetime import datetime

from pmg import db


class SoundcloudTrack(db.Model):

    __tablename__ = "soundcloud_track"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    modified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    file_id = db.Column(
        db.Integer,
        db.ForeignKey('file.id', ondelete='CASCADE'),
        nullable=False
    )
    uri = db.Column(db.String())
    state = db.Column(db.String())

    def __init__(self, file, track):
        self.file_id = file.id
        self.uri = track.uri
        self.state = track.state
