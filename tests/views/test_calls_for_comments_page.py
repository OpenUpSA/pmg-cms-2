from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, CallForCommentData
import urllib.request, urllib.error, urllib.parse


class TestCallsForCommentsPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCallsForCommentsPage, self).setUp()

        self.fx = dbfixture.data(CallForCommentData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCallsForCommentsPage, self).tearDown()

    def test_calls_for_comments(self):
        """
        Test calls for comments page (/calls-for-comments/)
        """
        call_for_comment = self.fx.CallForCommentData.arts_call_for_comment_one
        self.make_request("/calls-for-comments/")
        self.assertIn(call_for_comment.title, self.html)
