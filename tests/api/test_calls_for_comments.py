from tests import PMGTestCase
from tests.fixtures import dbfixture, CallForCommentData


class TestCallsForCommentsAPI(PMGTestCase):
    def setUp(self):
        super(TestCallsForCommentsAPI, self).setUp()

        self.fx = dbfixture.data(CallForCommentData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCallsForCommentsAPI, self).tearDown()

    def test_get_calls_for_comments(self):
        res = self.client.get(
            "/v2/calls-for-comments/?fields=id%2Ctitle%2Cclosed%2Cend_date%2Cstart_date&filter[house]=WC",
            base_url="http://api.pmg.test:5000/",
        )
        self.assertEqual(200, res.status_code)
