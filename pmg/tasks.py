from flask import current_app
from flask_script import Command
from pmg import db
import logging

log = logging.getLogger(__name__)


def send_saved_search_alerts():
    from pmg import app
    from pmg.models import SavedSearch

    with app.app_context():
        SavedSearch.send_all_alerts()


def update_active_committees():
    from pmg import app
    from pmg.models import Committee

    with app.app_context():
        Committee.update_active_committees()


def sync_soundcloud():
    from pmg import app
    from pmg.models.soundcloud_track import SoundcloudTrack

    with app.app_context():
        SoundcloudTrack.sync()


def schedule(scheduler):
    # from pmg import app

    # Schedule background task for sending saved search alerts every
    # day at 3am (UTC)
    jobs = [
        scheduler.add_job(
            "pmg.tasks:send_saved_search_alerts",
            "cron",
            id="send-saved-search-alerts",
            replace_existing=True,
            coalesce=True,
            hour=3,
        ),
        scheduler.add_job(
            update_active_committees,
            "cron",
            id="update-active-committees",
            replace_existing=True,
            coalesce=True,
            hour=2,
        ),
        scheduler.add_job(
            sync_soundcloud,
            "cron",
            id="sync-soundcloud",
            replace_existing=True,
            coalesce=True,
            minute="*/" + current_app.config["SOUNDCLOUD_PERIOD_MINUTES"],
        ),
    ]
    for job in jobs:
        log.info("Scheduled task: %s" % job)


class StartScheduler(Command):
    """
    Start APScheduler and queue scheduled tasks.

    Run with ``python app.py start_scheduler``.
    """

    def run(self):
        if not current_app.config["RUN_PERIODIC_TASKS"]:
            log.info(
                "Not starting task scheduler because RUN_PERIODIC_TASKS is not 'true'"
            )
            return

        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        import pmg.tasks

        scheduler = BlockingScheduler(
            {
                "apscheduler.jobstores.default": SQLAlchemyJobStore(engine=db.engine),
                "apscheduler.executors.default": {
                    "class": "apscheduler.executors.pool:ThreadPoolExecutor",
                    "max_workers": "2",
                },
                "apscheduler.timezone": "UTC",
            }
        )

        try:
            log.info("Scheduling tasks...")
            pmg.tasks.schedule(scheduler)
            log.info("Starting scheduler. Press Ctrl-C to exit.")
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass
