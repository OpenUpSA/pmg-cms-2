from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, DailyScheduleData


class TestDailySchedulesPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestDailySchedulesPage, self).setUp()

        self.fx = dbfixture.data(DailyScheduleData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestDailySchedulesPage, self).tearDown()

    def test_daily_schedules_page(self):
        """
        Test daily schedules page (/daily-schedules/)
        """
        self.make_request("/daily-schedules/", follow_redirects=True)
        self.assertIn("Daily Schedules", self.html)
        self.assertIn(self.fx.DailyScheduleData.schedule_one.title, self.html)
