import logging
import newrelic.agent

log = logging.getLogger(__name__)


def send_saved_search_alerts():
    from pmg import app
    from pmg.models import SavedSearch

    application = newrelic.agent.application()
    with newrelic.agent.BackgroundTask(application, name='send_saved_search_alerts', group='Task'):
        with app.app_context():
            SavedSearch.send_all_alerts()


def schedule():
    from pmg import scheduler
    # Schedule background task for sending saved search alerts every
    # day at 3am (UTC)
    job = scheduler.add_job('pmg.tasks:send_saved_search_alerts', 'cron',
                            id='send-saved-search-alerts', replace_existing=True,
                            coalesce=True, hour=14, minute=10)
    log.info("Scheduled task: %s" % job)
