from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, PostData
import flask

from pmg.models import db, Post


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
        Test blog post page (/blog/<slug>)
        """
        post = self.fx.PostData.the_week_ahead
        self.make_request("/blog/%s/" % post.slug)
        self.assertIn(post.title, self.html)
        self.assertIn(post.body[0:100], self.html)

    def test_blog_listings_page(self):
        """
        Test blog listings page (/blog)
        """
        self.make_request("/blog/")
        self.contains_template_text()
        self.contains_posts(Post.query.all())
        self.contains_archive()

    def test_blog_listings_page_with_filter(self):
        """
        Test blog listings page with a filter 
        (/blog?filter[month]=<month>&filter[year]=<year>).
        """
        month = "February"
        year = 2019
        self.make_request("/blog/?filter[month]=%s&filter[year]=%d" % (month, year))
        self.contains_template_text()
        self.contains_posts(
            [self.fx.PostData.first_term_review, self.fx.PostData.brief_explainer,]
        )
        self.doesnt_contain_posts(
            [self.fx.PostData.the_week_ahead, self.fx.PostData.government_priorities,]
        )
        self.contains_archive()

    def contains_template_text(self):
        self.assertIn("Blog", self.html)
        self.assertIn("Blog Archive", self.html)

    def contains_posts(self, posts):
        for post in posts:
            self.contains_blog_post(post)

    def contains_blog_post(self, post):
        self.assertIn(flask.escape(post.title), self.html)
        self.assertIn(flask.escape(post.body[0:200]), self.html)

    def doesnt_contain_posts(self, posts):
        for post in posts:
            self.doesnt_contain_blog_post(post)

    def doesnt_contain_blog_post(self, post):
        self.assertNotIn(flask.escape(post.title), self.html)

    def contains_archive(self):
        self.assertIn("2019 (3)", self.html)
        self.assertIn("2018 (1)", self.html)
        self.assertIn('January\n        <span class="count badge">1</span>', self.html)
        self.assertIn('February\n        <span class="count badge">2</span>', self.html)
        self.assertIn('August\n        <span class="count badge">1</span>', self.html)
