import os
from urllib.parse import urlparse, parse_qs
from builtins import str
from tests import PMGLiveServerTestCase
from unittest import skip
from pmg.models import db, Committee, CommitteeQuestion
from tests.fixtures import dbfixture, UserData, CommitteeData, MembershipData
from flask import escape
from io import BytesIO


class TestAdminCommitteeQuestions(PMGLiveServerTestCase):
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
        path = self.get_absolute_file_path("../data/RNW190-200303.docx")
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

        expected_contents = [
            "NW190",  # document name
            "Whether her Office has initiated the drafting of a Bill that seeks to protect and promote the rights",  # question
            "Minister in The Presidency for Women, Youth and Persons with Disabilities",  # minister
            "Mr S Ngcobo",  # asked by
            "The Department is in the process of preparing the drafting of a Bill which will be submitted to Cabinet",  # answer
        ]
        for contents in expected_contents:
            self.assertIn(
                contents, self.html,
            )

        # Delete the question that was created
        question = CommitteeQuestion.query.get(created_question_id)
        self.created_objects.append(question)

    @skip("Only test old format for now")
    def test_upload_committee_question_document_with_new_format(self):
        """
        Upload committee question document (/admin/committee-question/upload)
        """
        url = "/admin/committee-question/upload"
        data = {}
        path = self.get_absolute_file_path("../data/RNW104-2020-02-28.docx")
        with open(path, "rb") as f:
            data["file"] = (f, "RNW104-2020-02-28.docx")
            response = self.make_request(
                url,
                self.user,
                data=data,
                method="POST",
                headers={"Referer": "/admin/committee-question/"},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        self.assertEqual(200, response.status_code)

        expected_contents = [
            "What (a) is the number of (i) residential properties, (ii) business erven’, (iii) government buildings and (iv) agricultural properties owned by her department",  # question
            "The Minister of Public Works and Infrastructure",  # minister
            "Ms S J Graham",  # asked by
            "The Department of Public Works and Infrastructure (DPWI) has informed me that in the Lephalale Local Municipality the Department owns (i) 183 residential",  # answer
        ]
        for contents in expected_contents:
            self.assertIn(
                escape(contents), self.html,
            )

    def get_absolute_file_path(self, relative_path):
        dir_name = os.path.dirname(__file__)
        return os.path.join(dir_name, relative_path)
