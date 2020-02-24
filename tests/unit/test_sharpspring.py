from unittest.mock import patch

from pmg.sharpspring import Sharpspring
from tests import PMGTestCase


class TestSharpspring(PMGTestCase):
    @patch("pmg.sharpspring.requests.post")
    def test_make_sharpsrping_request(self, post_mock):
        sharpspring = Sharpspring()
        details = {
            "emailAddress": "test@example.com",
            "companyName": "Test Company",
        }
        sharpspring.call("createLeads", {"objects": [details]})
        post_mock.assertCalled()
