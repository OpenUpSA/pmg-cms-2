import os
from tests import PMGTestCase
from tests.fixtures import (
    dbfixture, CommitteeQuestionData
)


class TestQuestionAnswer(PMGTestCase):
    def setUp(self):
        super(TestQuestionAnswer, self).setUp()

        self.fx = dbfixture.data(
            CommitteeQuestionData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestQuestionAnswer, self).tearDown()

    def test_get_minister_questions_combined(self):
        response = self.client.get(
            "minister-questions-combined/",
            base_url="http://api.pmg.test:5000/"
        )
        results = response.json["results"]
        self.assertEqual(2, len(results))
        questions = [result['question'] for result in results]
        self.assertIn(self.fx.CommitteeQuestionData.arts_committee_question_one.question,
                      questions)
        self.assertIn(self.fx.CommitteeQuestionData.arts_committee_question_two.question,
                      questions)

    def test_get_minister_questions_combined_filter_by_year(self):
        response = self.client.get(
            "minister-questions-combined/?filter[year]=2018",
            base_url="http://api.pmg.test:5000"
        )
        results = response.json["results"]
        self.assertEqual(1, len(results))
        questions = [result['question'] for result in results]
        self.assertNotIn(self.fx.CommitteeQuestionData.arts_committee_question_one.question,
                         questions)
        self.assertIn(self.fx.CommitteeQuestionData.arts_committee_question_two.question,
                      questions)
