from tests import PMGLiveServerTestCase
from universal_analytics import Tracker
from unittest.mock import patch


class TestFilesPage(PMGLiveServerTestCase):
    @patch.object(Tracker, "send")
    def test_questions_file_page(self, mock_tracker):
        """
        Test files page (/questions/<path>)
        """
        path = "test_file.pdf"
        response = self.make_request(f"/questions/{path}", follow_redirects=False)
        mock_tracker.assert_called_with(
            "file_download",
            "/questions/test_file.pdf",
            referrer="",
            uip="127.0.0.1",
            userAgent="werkzeug/2.0.0",
        )
        self.assertEqual(302, response.status_code)
        static_host = self.app.config.get("STATIC_HOST")
        self.assertEqual(response.location, f"{static_host}questions/{path}")
