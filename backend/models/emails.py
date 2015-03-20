import re

from sqlalchemy import desc, func

from frontend import db

class EmailTemplate(db.Model):
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1024))
    subject = db.Column(db.String(100))
    body = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())

    @property
    def utm_campaign(self):
        return re.sub(r'[^a-z0-9 -]+', '', self.name.lower()).replace(' ', '-')
