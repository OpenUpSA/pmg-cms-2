from pmg import app
from pmg.models.soundcloud_track import SoundcloudTrack
from flask.ext.script import Server, Manager
from flask.ext.migrate import MigrateCommand

app.debug = True

manager = Manager(app)
manager.add_command("runserver", Server(port=5000, threaded=True, host="0.0.0.0"))
manager.add_command("db", MigrateCommand)


@manager.command
def sync_soundcloud():
    SoundcloudTrack.sync()


if __name__ == "__main__":
    manager.run()
