from mock import patch
from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, HouseData
)
from pyelasticsearch import ElasticSearch


class TestSearchPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestSearchPage, self).setUp()

        self.fx = dbfixture.data(
            HouseData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestSearchPage, self).tearDown()

    @patch.object(ElasticSearch, 'search')
    def __call__(self, result=None, search_mock=None):
        search_mock.return_value = {
            u'hits': {
                u'hits': [], u'total': 1, u'max_score': 1.1129572
            }, u'_shards': {
                u'successful': 5, u'failed': 1, u'total': 5
            },
            u'took': 167, u'aggregations': {
                u'types': {
                    u'types': {
                        u'buckets': [
                            {u'key': u'post', u'doc_count': 1},
                            {u'key': u'committee', u'doc_count': 1}
                        ],
                        u'sum_other_doc_count': 0, u'doc_count_error_upper_bound': 0
                    }, u'doc_count': 1
                }, u'years': {
                    u'years': {
                        u'buckets': [{
                            u'key_as_string': u'2019-01-01T00:00:00.000Z',
                            u'key': 1546300800000, u'doc_count': 1
                        },{
                            u'key_as_string': u'2018-01-01T00:00:00.000Z',
                            u'key': 1546300800000, u'doc_count': 1
                        }]}, u'doc_count': 1
                }
            }, u'timed_out': False
        }
        super(TestSearchPage, self).__call__(result)

    def test_search_page(self):
        search_term = 'content'
        self.get_page_contents(
            "http://pmg.test:5000/search/?q=%s" % search_term
        )
        self.assertIn(search_term, self.html)
        self.assertIn('Blog Posts', self.html)
        self.assertIn('Committees', self.html)
        self.assertIn('2018', self.html)
        self.assertIn('2019', self.html)
