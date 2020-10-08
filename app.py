from pmg import app, StartScheduler
from pmg.models.soundcloud_track import SoundcloudTrack
from flask_script import Server, Manager
from flask_migrate import MigrateCommand

app.debug = True

manager = Manager(app)
manager.add_command("runserver", Server(port=5000, threaded=True, host="0.0.0.0"))
manager.add_command("db", MigrateCommand)
manager.add_command("start_scheduler", StartScheduler)


@manager.command
def sync_soundcloud():
    SoundcloudTrack.sync()


if __name__ == "__main__":
    manager.run()
