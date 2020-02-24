from unittest.mock import patch

from pmg.sharpspring import Sharpspring
from tests import PMGTestCase


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self.json_data


def mocked_requests_post_success(*args, **kwargs):

    return MockResponse({"result": {"creates": [{"success": True,}]}}, 200)


class TestSharpspring(PMGTestCase):
    @patch("pmg.sharpspring.requests.post", side_effect=mocked_requests_post_success)
    def test_make_sharpsrping_request(self, post_mock):
        sharpspring = Sharpspring()
        details = {
            "emailAddress": "test@example.com",
            "companyName": "Test Company",
        }
        result = sharpspring.call("createLeads", {"objects": [details]})
        post_mock.assert_called()
        self.assertTrue(result["result"]["creates"][0])
