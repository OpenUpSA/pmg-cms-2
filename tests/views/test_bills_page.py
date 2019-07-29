from tests import PMGLiveServerTestCase


class TestBillsPage(PMGLiveServerTestCase):
    def test_bills_page(self):
        self.get_page_contents("http://pmg.test:5000/bills")
        headings = ['Current Bills', 'All Tabled Bills',
                    'Private Member &amp; Committee Bills',
                    'All Tabled &amp; Draft Bills',
                    'Draft Bills', 'Bills Explained']
        for heading in headings:
            self.assertIn(heading, self.html)
