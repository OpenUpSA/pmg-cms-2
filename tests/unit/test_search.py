import unittest
from mock import patch
from nose.tools import *  # noqa
import arrow

from pmg.models import db, CommitteeMeeting
from pmg.search import Search


class TestSearch(unittest.TestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    @patch.object(Search, 'add_obj')
    @patch.multiple(Search, reindex_changes=True)
    def test_new_object_reindexed(self, add_obj):
        cm = CommitteeMeeting()
        cm.date = arrow.now().datetime
        cm.title = "Foo"
        db.session.add(cm)
        db.session.commit()

        assert_true(Search.add_obj.called)

    @patch.object(Search, 'add_obj')
    @patch.multiple(Search, reindex_changes=True)
    def test_updated_object_reindexed(self, add_obj):
        cm = CommitteeMeeting()
        cm.date = arrow.now().datetime
        cm.title = "Foo"
        db.session.add(cm)
        db.session.commit()

        assert_true(Search.add_obj.called)
        Search.add_obj.reset_mock()

        # now update it
        cm.title = "Updated"
        db.session.commit()
        assert_true(Search.add_obj.called)

    @patch.object(Search, 'add_obj')
    @patch.object(Search, 'delete_obj')
    @patch.multiple(Search, reindex_changes=True)
    def test_deleted_object_reindexed(self, add_obj, delete_obj):
        cm = CommitteeMeeting()
        cm.date = arrow.now().datetime
        cm.title = "Foo"
        db.session.add(cm)
        db.session.commit()

        assert_true(Search.add_obj.called)
        Search.add_obj.reset_mock()

        # now delete it
        db.session.delete(cm)
        db.session.commit()
        assert_false(Search.add_obj.called)
        assert_true(Search.delete_obj.called)
