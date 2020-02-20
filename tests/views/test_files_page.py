from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData
from unittest.mock import patch


class TestFilesPage(PMGLiveServerTestCase):
    @patch('pmg.views.utils.track_pageview')
    def test_questions_file_page(self, mock_tracker):
        """
        Test email alerts page (/questions/<path>)
        """
        path = "test_file.pdf"
        response = self.make_request(f"/questions/{path}", follow_redirects=False)
        mock_tracker.assert_called()
        self.assertEqual(302, response.status_code)
        print(response.location)
        static_host = self.app.config.get("STATIC_HOST")
        self.assertEqual(response.location, f'{static_host}questions/{path}')
