from pmg import app
from pmg.models.soundcloud_track import SoundcloudTrack
from flask.ext.script import Server, Manager
from flask.ext.migrate import MigrateCommand

manager = Manager(app)
manager.add_command('runserver', Server(port=5000, threaded=True))
manager.add_command('db', MigrateCommand)


@manager.command
def sync_soundcloud():
    SoundcloudTrack.sync()

if __name__ == '__main__':
    manager.run()
