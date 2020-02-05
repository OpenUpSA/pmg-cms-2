from tests import PMGLiveServerTestCase
from mock import patch
import unittest
from pmg.models import db, BillType, Minister, Bill
from tests.fixtures import (
    dbfixture,
    EmailTemplateData,
    UserData,
    HouseData,
    CommitteeData,
)


class TestAdminAlertsPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminAlertsPage, self).setUp()

        self.fx = dbfixture.data(EmailTemplateData, HouseData, CommitteeData, UserData)
        self.fx.setup()
        self.user = self.fx.UserData.admin
        self.create_alert_data = {
            "template_id": self.fx.EmailTemplateData.template_one.id,
            "previewed": 1,
            "committee_meeting_id": "",
            "from_email": "test@example.com",
            "subject": self.fx.EmailTemplateData.template_one.subject,
            "body": self.fx.EmailTemplateData.template_one.body,
            "committee_ids": self.fx.CommitteeData.arts.id,
        }

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminAlertsPage, self).tearDown()

    def test_admin_alerts_page(self):
        """
        Test admin alerts page (/admin/alerts)
        """
        self.make_request("/admin/alerts", self.user, follow_redirects=True)
        self.assertIn("Send an email alert", self.html)
        self.assertIn("What template would you like to use?", self.html)
        self.assertIn(
            'If none of these are suitable, <a href="/admin/email-templates/new/">create a new template',
            self.html,
        )
        self.assertIn(self.fx.EmailTemplateData.template_one.name, self.html)

    def test_admin_alerts_new_page(self):
        """
        Test admin new alerts page (/admin/alerts/new)
        """
        self.make_request(
            "/admin/alerts/new?template_id=%d"
            % self.fx.EmailTemplateData.template_one.id,
            self.user,
            follow_redirects=True,
        )
        self.assertIn(
            "Send an email alert: %s" % self.fx.EmailTemplateData.template_one.name,
            self.html,
        )
        self.assertIn("Committee Recipients", self.html)
        committee_name_format = "%s - %s (%d)" % (
            self.fx.CommitteeData.arts.house.name,
            self.fx.CommitteeData.arts.name,
            3,
        )
        self.assertIn(committee_name_format, self.html)

    def test_post_admin_alerts_new_page_preview(self):
        """
        Test admin new alerts page preview (/admin/alerts/preview)
        """
        response = self.make_request(
            "/admin/alerts/preview",
            self.user,
            data=self.create_alert_data,
            method="POST",
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertIn("Subject", self.html)
        self.assertIn(self.fx.EmailTemplateData.template_one.subject, self.html)

    @patch("pmg.admin.email_alerts.send_sendgrid_email", return_value=True)
    def test_post_admin_alerts_new_page(self, mock):
        """
        Test submit admin new alerts page (/admin/alerts/new)
        """
        response = self.make_request(
            "/admin/alerts/new",
            self.user,
            data=self.create_alert_data,
            method="POST",
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "Your email alert with subject &#39;%s&#39; has been sent to %d recipients."
            % (self.fx.EmailTemplateData.template_one.subject, 3),
            self.html,
        )
