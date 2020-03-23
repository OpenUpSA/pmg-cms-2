import os
from builtins import str
from tests import PMGLiveServerTestCase
from pmg.models import db, Committee
from tests.fixtures import dbfixture, UserData, CommitteeData, MembershipData
from werkzeug.datastructures import FileStorage
from io import BytesIO


class TestAdminCommitteeQuestions(PMGLiveServerTestCase):
    def setUp(self):
        super().setUp()

        self.fx = dbfixture.data(UserData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

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
                follow_redirects=True,
            )
        self.assertEqual(200, response.status_code)

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

    def get_absolute_file_path(self, relative_path):
        dir_name = os.path.dirname(__file__)
        return os.path.join(dir_name, relative_path)
