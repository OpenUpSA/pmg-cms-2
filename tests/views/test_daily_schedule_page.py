from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, DailyScheduleData


class TestDailySchedulePage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestDailySchedulePage, self).setUp()

        self.fx = dbfixture.data(DailyScheduleData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestDailySchedulePage, self).tearDown()

    def test_daily_schedule_page(self):
        """
        Test daily schedule page for schedule (/daily-scheduleis/<id>/)
        """
        self.make_request(
            "/daily-schedule/%s/" % self.fx.DailyScheduleData.schedule_provincial.id,
            follow_redirects=True,
        )
        self.assertIn("Daily Schedules", self.html)
        self.assertIn(self.fx.DailyScheduleData.schedule_provincial.title, self.html)
