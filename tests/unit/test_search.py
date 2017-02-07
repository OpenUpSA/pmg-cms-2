from mock import patch
from nose.tools import *  # noqa
import arrow

from tests import PMGTestCase
from pmg import app
from pmg.models import db, CommitteeMeeting
from pmg.search import Search
from pyelasticsearch import ElasticSearch


class TestSearch(PMGTestCase):
    @patch.object(ElasticSearch, 'bulk_index')
    @patch.multiple(Search, reindex_changes=True)
    def test_new_object_reindexed(self, bulk_index):
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk_index.called)

    @patch.object(ElasticSearch, 'bulk_index')
    @patch.multiple(Search, reindex_changes=True)
    def test_updated_object_reindexed(self, bulk_index):
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk_index.called)
            bulk_index.reset_mock()

            # now update it
            cm.title = "Updated"
            db.session.commit()
            assert_true(bulk_index.called)

    @patch.object(ElasticSearch, 'bulk_index')
    @patch.object(ElasticSearch, 'delete')
    @patch.multiple(Search, reindex_changes=True)
    def test_deleted_object_reindexed(self, delete, bulk_index):
        with app.app_context():
            cm = CommitteeMeeting()
            cm.date = arrow.now().datetime
            cm.title = "Foo"
            db.session.add(cm)
            db.session.commit()

            assert_true(bulk_index.called)
            bulk_index.reset_mock()

            # now delete it
            db.session.delete(cm)
            db.session.commit()
            assert_false(bulk_index.called)
            assert_true(delete.called)
