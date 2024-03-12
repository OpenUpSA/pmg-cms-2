from tests import PMGLiveServerTestCase
from unittest.mock import patch


class TestFilesPage(PMGLiveServerTestCase):
    def test_questions_file_page(self):
        """
        Test files page (/questions/<path>)
        """
        path = "test_file.pdf"
        response = self.make_request(f"/questions/{path}", follow_redirects=False)

        self.assertEqual(302, response.status_code)
        self.assertEqual("http://pmg-assets.s3-website-eu-west-1.amazonaws.com/questions/test_file.pdf", response.location)
        static_host = self.app.config.get("STATIC_HOST")
        self.assertEqual(response.location, f"{static_host}questions/{path}")
