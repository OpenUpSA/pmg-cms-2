from mock import patch, MagicMock
from nose.tools import *  # noqa
import arrow

from tests import PMGTestCase
from pmg import app
from pmg.models import db, CommitteeMeeting, Post
from pmg.search import Search, Transforms
from elasticsearch import Elasticsearch


class TestSearch(PMGTestCase):
    @patch.object(Elasticsearch, "bulk")
    @patch.multiple(Search, reindex_changes=True)
    def test_new_object_reindexed(self, bulk):
        bulk.return_value = {"errors": False, "items": []}
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk.called)

    @patch.object(Elasticsearch, "bulk")
    @patch.multiple(Search, reindex_changes=True)
    def test_updated_object_reindexed(self, bulk):
        bulk.return_value = {"errors": False, "items": []}
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk.called)
            bulk.reset_mock()

            # now update it
            cm.title = "Updated"
            db.session.commit()
            assert_true(bulk.called)

    @patch.object(Elasticsearch, "bulk")
    @patch.object(Elasticsearch, "delete")
    @patch.multiple(Search, reindex_changes=True)
    def test_deleted_object_reindexed(self, delete, bulk):
        bulk.return_value = {"errors": False, "items": []}
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk.called)
            bulk.reset_mock()

            # now delete it
            db.session.delete(cm)
            db.session.commit()
            assert_false(bulk.called)
            assert_true(delete.called)

    @patch.object(Elasticsearch, "bulk")
    @patch.multiple(Search, reindex_changes=True)
    def test_index_blog_post(self, bulk):
        bulk.return_value = {"errors": False, "items": []}
        with app.app_context():
            post = self.create_post()

            assert_true(bulk.called)

    def test_search_data_types(self):
        models_to_index = [
            "committee",
            "committee_meeting",
            "minister_question",
            "member",
            "bill",
            "hansard",
            "briefing",
            "post",
            "tabled_committee_report",
            "call_for_comment",
            "policy_document",
            "gazette",
            "daily_schedule",
        ]
        data_types = Transforms.data_types()

        for model in models_to_index:
            assert_in(model, data_types)

    def test_serialise_post(self):
        with app.app_context():
            post = self.create_post()

            data = Transforms.serialise(post)
            assert_equals(post.title, data["title"])
            assert_in("Blog post header", data["fulltext"])
            assert_not_in("<h1>", data["fulltext"])
            assert_equals(post.slug, data["slug"])
            assert_equals(post.date.isoformat(), data["date"])

    def create_post(self):
        post = Post()
        post.date = arrow.now().datetime
        post.title = "The Blog post"
        post.slug = "blog-post"
        post.body = (
            "<p><h1>Blog post header</h1></p><p>&nbsp;</p>"
            "<p><a href='/'>Zebra link</a></p>"
        )
        db.session.add(post)
        db.session.commit()

        return post
