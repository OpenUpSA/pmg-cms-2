from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, PostData
import urllib2


class TestBlogPages(PMGLiveServerTestCase):
    def setUp(self):
        super(TestBlogPages, self).setUp()

        self.fx = dbfixture.data(PostData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestBlogPages, self).tearDown()

    def test_blog_post_page(self):
        """
        Test blog post page (http://pmg.test:5000/blog/<slug>)
        """
        post = self.fx.PostData.the_week_ahead
        self.get_page_contents(
            "http://pmg.test:5000/blog/%s/"
            % post.slug
        )
        self.assertIn(post.title, self.html)
        self.assertIn(post.body[0:100], self.html)
        self.assertIn('That week in Parliament', self.html)

    def test_blog_post_page(self):
        """
        Test blog post page (http://pmg.test:5000/blog/<slug>)
        """
        post = self.fx.PostData.the_week_ahead
        self.get_page_contents(
            "http://pmg.test:5000/blog/%s/"
            % post.slug
        )
        self.assertIn(post.title, self.html)
        self.assertIn(post.body[0:100], self.html)
        self.assertIn('That week in Parliament', self.html)