import os
from urllib.parse import urlparse, parse_qs
from tests import PMGLiveServerTestCase
from pmg.models import db, CommitteeQuestion
from tests.fixtures import dbfixture, UserData


class TestAdminCommitteeQuestions(PMGLiveServerTestCase):
    maxDiff = None
    def setUp(self):
        super().setUp()

        self.fx = dbfixture.data(UserData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super().tearDown()

    def test_upload_committee_question_document_with_old_format(self):
        """
        Upload committee question document (/admin/committee-question/upload)
        """
        url = "/admin/committee-question/upload"
        data = {}
        path = self.get_absolute_file_path(
            "../data/committee_questions/RNW190-200303.docx"
        )
        with open(path, "rb") as f:
            data["file"] = (f, "RNW190-200303.docx")
            response = self.make_request(
                url,
                self.user,
                data=data,
                method="POST",
                headers={"Referer": "/somethingelse"},
                content_type="multipart/form-data",
            )
        self.assertEqual(302, response.status_code)

        response_url = urlparse(response.location)
        response_query = parse_qs(response_url.query)
        self.assertIn("id", response_query, "Question ID must be in response query")
        created_question_id = int(response_query["id"][0])

        response = self.make_request(
            "%s?%s" % (response_url.path, response_url.query),
            self.user,
            follow_redirects=True,
        )

        self.assertEqual(200, response.status_code)

        # Test that the question that was created contains the correct data
        question = CommitteeQuestion.query.get(created_question_id)

        self.assertEqual(
            question.question,
            "Whether her Office has initiated the drafting of a Bill that seeks to protect and promote the rights of persons with disabilities; if not, (a) why not and (b) what steps does her Office intend taking in this regard; if so, on what date does she envisage that the Bill will be introduced in the National Assembly?",
        )
        self.assertEqual(
            question.minister.name,
            "Minister in The Presidency for Women, Youth and Persons with Disabilities",
        )
        self.assertEqual(question.asked_by_name, "Mr S Ngcobo")
        self.assertEqual(
            question.answer,
            "<p>Yes</p><p>(b) The Department is in the process of preparing the drafting of a Bill which will be submitted to Cabinet for approval before it will be tabled in Parliament during the 2021/2022 financial year.</p>",
        )
        self.assertEqual(question.code, "NW190")

        # Delete the question that was created
        self.created_objects.append(question)

    def test_upload_committee_question_document_with_new_format(self):
        """
        Upload committee question document (/admin/committee-question/upload)
        """
        url = "/admin/committee-question/upload"
        data = {}
        path = self.get_absolute_file_path(
            "../data/committee_questions/RNW104-2020-02-28.docx"
        )
        with open(path, "rb") as f:
            data["file"] = (f, "RNW104-2020-02-28.docx")
            response = self.make_request(
                url,
                self.user,
                data=data,
                method="POST",
                headers={"Referer": "/admin/committee-question/"},
                content_type="multipart/form-data",
            )
        self.assertEqual(302, response.status_code)

        response_url = urlparse(response.location)
        response_query = parse_qs(response_url.query)
        self.assertIn("id", response_query, "Question ID must be in response query")
        created_question_id = int(response_query["id"][0])

        response = self.make_request(
            "%s?%s" % (response_url.path, response_url.query),
            self.user,
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)

        # Test that the question that was created contains the correct data
        question = CommitteeQuestion.query.get(created_question_id)
        self.assertEqual(
            question.question,
            "What (a) is the number of (i) residential properties, (ii) business erven’, (iii) government buildings and (iv) agricultural properties owned by her department in the Lephalale Local Municipality which are (aa) vacant, (bb) occupied and (cc) earmarked for disposal and (b) total amount does her department owe the municipality in outstanding rates and services?",
        )
        self.assertEqual(
            question.minister.name,
            "Minister of Public Works and Infrastructure",
        )
        self.assertEqual(question.asked_by_name, "Ms S J Graham")
        self.assertEqual.__self__.maxDiff = None
        print("*****************************************")
        print(question.answer)
        self.assertEqual(
            question.answer,
            "<p><strong>The Minister of Public Works and Infrastructure: </strong></p><ol><li>The Department of Public Works and Infrastructure (DPWI) has informed me that in the Lephalale Local Municipality the Department owns (i) 183 residential properties (ii) one business erven (iii) 132 government buildings and (iv) 5 agricultural properties.  DPWI informed me that (aa) 8 land parcels are vacant and (bb) only one property is unutilised. </li></ol><p>(cc)  DPWI has not earmarked any properties for disposal in the Lephalale Local Municipality.</p><ol><li>In August 2019 the Department started a Government Debt Project engaging directly with municipalities and Eskom to verify and reconcile accounts and the project. DPWI, on behalf of client departments, owed the Lephalale Local Municipality, as per accounts received on 17 February 2020, R 334,989.69 which relates current consumption. </li></ol>",
        )
        print("*****************************************")
        self.assertEqual(question.code, "NW104")

        # Delete the question that was created
        self.created_objects.append(question)

    def test_upload_committee_question_document_with_navigable_string_error(self):
        """
        Upload committee question document (/admin/committee-question/upload)
        """
        url = "/admin/committee-question/upload"
        data = {}
        path = self.get_absolute_file_path(
            "../data/committee_questions/RNW1153-200619.docx"
        )
        with open(path, "rb") as f:
            data["file"] = (f, "RNW1153-200619.docx")
            response = self.make_request(
                url,
                self.user,
                data=data,
                method="POST",
                headers={"Referer": "/admin/committee-question/"},
                content_type="multipart/form-data",
            )
        self.assertEqual(302, response.status_code)

        response_url = urlparse(response.location)
        response_query = parse_qs(response_url.query)
        self.assertIn("id", response_query, "Question ID must be in response query")
        created_question_id = int(response_query["id"][0])

        response = self.make_request(
            "%s?%s" % (response_url.path, response_url.query),
            self.user,
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)

        # Test that the question that was created contains the correct data
        question = CommitteeQuestion.query.get(created_question_id)
        self.assertIn(
            "(1)\tWhether, with reference to her reply to question 937 on 4 June 2020",
            question.question,
        )
        self.assertEqual(
            question.minister.name,
            "Minister in The Presidency for Women, Youth and Persons with Disabilities",
        )
        self.assertEqual(question.asked_by_name, "Ms T Breedt")
        self.assertIn(
            "There were no deviations from the standard supply chain management procedures",
            question.answer,
        )
        self.assertEqual(question.code, "NW1153")

        # Delete the question that was created
        self.created_objects.append(question)

    def get_absolute_file_path(self, relative_path):
        dir_name = os.path.dirname(__file__)
        return os.path.join(dir_name, relative_path)
