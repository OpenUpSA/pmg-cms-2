from tests import PMGTestCase
from tests.fixtures import dbfixture, BillData, BillTypeData


class TestBillAPI(PMGTestCase):
    def setUp(self):
        super(TestBillAPI, self).setUp()
        self.fx = dbfixture.data(BillTypeData, BillData)
        self.fx.setup()

    def test_total_bill(self):
        """
        Viewing all private member bills
        """
        res = self.client.get('bill/', base_url='http://api.pmg.test:5000/')
        self.assertEqual(200, res.status_code)
        self.assertEqual(4, res.json['count'])

    def test_private_memeber_bill(self):
        """
        Count the total number of private bills
        """
        res = self.client.get(
            'bill/pmb/', base_url='http://api.pmg.test:5000/')
        self.assertEqual(200, res.status_code)
        self.assertEqual(2, res.json['count'])
