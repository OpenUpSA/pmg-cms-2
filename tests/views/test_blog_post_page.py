from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, PostData
import urllib2
import flask
from sqlalchemy import func
from collections import defaultdict

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

    def test_blog_listings_page(self):
        """
        Test blog listings page (http://pmg.test:5000/blog)
        """
        self.get_page_contents("http://pmg.test:5000/blog")
        self.contains_template_text()
        self.contains_posts()
        self.contains_archive()
    
    def contains_template_text(self):
        self.assertIn('That week in Parliament', self.html)
        self.assertIn('About this blog', self.html)
        self.assertIn('Blog Archive', self.html)

    def contains_posts(self):
        for post in Post.query.all():
            self.contains_blog_post(post)

    def contains_blog_post(self, post):
        self.assertIn(flask.escape(post.title), self.html)
        self.assertIn(flask.escape(post.body[0:200]), self.html)

    def contains_archive(self):
        self.assertIn("2019 (3)", self.html)
        self.assertIn("2018 (1)", self.html)
        self.assertIn('January\n        <span class="count badge">1</span>', self.html)
        self.assertIn('February\n        <span class="count badge">2</span>', self.html)
        self.assertIn('August\n        <span class="count badge">1</span>', self.html)
