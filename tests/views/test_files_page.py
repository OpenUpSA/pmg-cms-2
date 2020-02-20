from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData
from universal_analytics import Tracker
from unittest.mock import patch


def mock_send(*args, **kwargs):
    return True

class TestFilesPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestFilesPage, self).setUp()
        # self.app.config.set("GOOGLE_ANALYTICS_ID", 'test-id')

    @patch.object(Tracker, 'send', mock_send)
    def test_questions_file_page(self):
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
