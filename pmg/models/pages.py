import re

from sqlalchemy import desc, func
from sqlalchemy.orm import validates

from pmg import app, db
from .base import resource_slugs


class Redirect(db.Model):
    __tablename__ = 'redirect'

    id = db.Column(db.Integer, primary_key=True)
    nid = db.Column(db.Integer)
    old_url = db.Column(db.String(250), nullable=False, unique=True, index=True)
    new_url = db.Column(db.String(250))

    def __str__(self):
        if self.nid:
            target = "nid %s" % self.nid
        else:
            target = self.new_url

        return u'<Redirect from %s to %s>' % (self.old_url, target)

    @classmethod
    def object_for_nid(cls, nid):
        for cls in resource_slugs.itervalues():
            if hasattr(cls, 'nid'):
                obj = cls.query.filter(cls.nid == nid).first()
                if obj:
                    return obj

    @classmethod
    def for_url(cls, old_url):
        dest = None
        nid = None

        if old_url.endswith("/"):
            old_url = old_url[:-1]

        # check for /node/1234
        match = re.match('^/node/(\d+)$', old_url)
        if match:
            nid = match.group(1)

        else:
            redirect = cls.query.filter(cls.old_url == old_url).first()
            if redirect:
                if redirect.new_url:
                    dest = redirect.new_url
                elif redirect.nid:
                    nid = redirect.nid

        if nid:
            # lookup based on nid
            obj = cls.object_for_nid(nid)
            if obj:
                dest = obj.url_path()

        if dest and not dest.startswith('/'):
            dest = '/' + dest

        return dest


class Page(db.Model):
    """ A basic CMS page. """
    __tablename__ = 'page'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False, unique=True, index=True)
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())

    @validates('slug')
    def validate_slug(self, key, value):
        return value.strip('/')
