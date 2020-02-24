from unittest.mock import patch

from pmg.sharpspring import Sharpspring
from tests import PMGTestCase
from tests.fixtures import dbfixture, UserData, OrganisationData
from pmg.models import User, Organisation


SHARPSRING_URL = "http://api.sharpspring.com/pubapi/v1/"


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self.json_data


def mocked_requests_post_success(*args, **kwargs):
    return MockResponse(
        {"result": {"creates": [{"success": True,}]}, "error": False}, 200
    )


class TestSharpspring(PMGTestCase):
    def setUp(self):
        super(TestSharpspring, self).setUp()

        self.fx = dbfixture.data(UserData, OrganisationData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestSharpspring, self).tearDown()

    @patch("pmg.sharpspring.requests.post", side_effect=mocked_requests_post_success)
    def test_make_sharpspring_request(self, post_mock):
        sharpspring = Sharpspring()
        details = {
            "emailAddress": "test@example.com",
            "companyName": "Test Company",
        }
        result = sharpspring.call("createLeads", {"objects": [details]})
        post_mock.assert_called()
        self.assertTrue(result["result"]["creates"][0])

    @patch.object(
        Sharpspring,
        "call",
        return_value={"result": {"creates": [{"success": True,}]}, "error": False},
    )
    def test_subscribe_to_list_success(self, sharpspring_call_mock):
        user = self.fx.UserData.admin

        sharpspring = Sharpspring()
        sharpspring.subscribeToList(user, "1234")
        sharpspring_call_mock.assert_any_call(
            "createLeads",
            {
                "objects": [
                    {"emailAddress": user.email, "companyName": user.organisation.name}
                ]
            },
        )
        sharpspring_call_mock.assert_any_call(
            "addListMemberEmailAddress", {"emailAddress": user.email, "listID": "1234"}
        )

    @patch.object(
        Sharpspring,
        "call",
        return_value={
            "result": {"creates": [{"success": False, "error": {"code": 500}}]}
        },
    )
    def test_subscribe_to_list_fail(self, sharpspring_call_mock):
        user = self.fx.UserData.admin

        sharpspring = Sharpspring()
        self.assertRaises(ValueError, sharpspring.subscribeToList, user, "1234")
