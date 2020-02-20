from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, CommitteeQuestionData


class TestQuestionRepliesPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestQuestionRepliesPage, self).setUp()

        self.fx = dbfixture.data(CommitteeQuestionData,)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestQuestionRepliesPage, self).tearDown()

    def test_question_replies_page(self):
        """
        Test Questions and Replies page (/question_replies).
        """
        question = self.fx.CommitteeQuestionData.arts_committee_question_one
        self.make_request("/question_replies/")
        self.assertIn("Questions and Replies", self.html)
        self.assertIn("Filter by year", self.html)
        self.assertIn("2019", self.html)
        self.assertIn("2018", self.html)
        self.assertIn(question.question, self.html)

    def test_question_replies_page_with_year_filter(self):
        """
        Test Questions and Replies page with filter by year 
        (/question_replies/?filter[year]=2018).
        """
        question_2019 = self.fx.CommitteeQuestionData.arts_committee_question_one
        question_2018 = self.fx.CommitteeQuestionData.arts_committee_question_two
        self.make_request("/question_replies/?filter[year]=2018")
        self.assertIn(question_2018.question, self.html)
        self.assertNotIn(question_2019.question, self.html)

    def test_question_replies_page_with_year_and_minister_filter(self):
        """
        Test Questions and Replies page with filter by year and minister
        (/question_replies/?filter[year]=2018&filter[minister]=2).
        """
        question_2019 = self.fx.CommitteeQuestionData.arts_committee_question_one
        question_2018 = self.fx.CommitteeQuestionData.arts_committee_question_two
        self.make_request("/question_replies/?filter[year]=2018")
        self.assertIn(question_2018.question, self.html)
        self.assertNotIn(question_2019.question, self.html)
