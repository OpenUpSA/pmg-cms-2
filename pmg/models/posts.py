from builtins import str
from sqlalchemy import func, sql
from sqlalchemy.orm import validates

from .base import FileLinkMixin, ApiResource

from pmg import db


class Post(ApiResource, db.Model):
    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False, unique=True, index=True)
    featured = db.Column(
        db.Boolean(),
        default=False,
        server_default=sql.expression.false(),
        nullable=False,
        index=True,
    )
    body = db.Column(db.Text)
    date = db.Column(
        db.DateTime(timezone=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=func.now(),
    )
    files = db.relationship("PostFile", lazy="joined", cascade="all, delete-orphan")
    created_at = db.Column(
        db.DateTime(timezone=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )

    def get_preview_image(self):
        if self.files:
            return self.files[0].file
        else:
            return None

    @validates("slug")
    def validate_slug(self, key, value):
        return value.strip("/")

    def __str__(self):
        return str(self.title)


class PostFile(FileLinkMixin, db.Model):
    __tablename__ = "post_files"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    post = db.relationship("Post")
    file_id = db.Column(
        db.Integer,
        db.ForeignKey("file.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file = db.relationship("File", lazy="joined")


# Register all the resource types. This ensures they show up in the API and are searchable
ApiResource.register(Post)
