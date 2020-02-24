from unittest.mock import patch

from pmg.sharpspring import Sharpspring
from tests import PMGTestCase
from tests.fixtures import dbfixture, UserData, OrganisationData
from requests import HTTPError


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if 400 <= self.status_code < 500 or 500 <= self.status_code < 600:
            raise HTTPError()

    def json(self):
        return self.json_data


def get_requests_post_success(*args, **kwargs):
    return MockResponse(
        {"result": {"creates": [{"success": True,}]}, "error": False}, 200
    )


def get_sharpspring_call_success(*args, **kwargs):
    return {"result": {"creates": [{"success": True,}]}, "error": False}


def get_sharpspring_call_fail_create_lead(*args, **kwargs):
    return {"result": {"creates": [{"success": False, "error": {"code": 302}}]}}


def get_sharpspring_call_fail_add_list_member(method, params):
    if method == "createLeads":
        return {"result": {"creates": [{"success": True,}]}, "error": False}
    else:
        return {
            "result": {"creates": [{"success": False, "error": {"code": 302}}]},
            "error": {"code": 302},
        }


class TestSharpspring(PMGTestCase):
    def setUp(self):
        super(TestSharpspring, self).setUp()

        self.fx = dbfixture.data(UserData, OrganisationData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestSharpspring, self).tearDown()

    @patch("pmg.sharpspring.requests.post", side_effect=get_requests_post_success)
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
        Sharpspring, "call", return_value=get_sharpspring_call_success(),
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
        Sharpspring, "call", return_value=get_sharpspring_call_fail_create_lead(),
    )
    def test_subscribe_to_list_create_lead_fail(self, sharpspring_call_mock):
        user = self.fx.UserData.admin

        sharpspring = Sharpspring()
        self.assertRaises(ValueError, sharpspring.subscribeToList, user, "1234")

    @patch.object(
        Sharpspring, "call", side_effect=get_sharpspring_call_fail_add_list_member,
    )
    def test_subscribe_to_list_add_member_fail(self, sharpspring_call_mock):
        user = self.fx.UserData.admin

        sharpspring = Sharpspring()
        self.assertRaises(ValueError, sharpspring.subscribeToList, user, "1234")

    @patch("pmg.sharpspring.requests.post", return_value=MockResponse({}, 500))
    def test_subscribe_to_list_server_fail(self, sharpspring_call_mock):
        user = self.fx.UserData.admin

        sharpspring = Sharpspring()
        self.assertRaises(HTTPError, sharpspring.subscribeToList, user, "1234")
