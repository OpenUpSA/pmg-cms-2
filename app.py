from pmg import app
import pmg.sync_soundcloud as soundcloud
from flask.ext.script import Server, Manager
from flask.ext.migrate import MigrateCommand

manager = Manager(app)
manager.add_command('runserver', Server(port=5000, threaded=True))
manager.add_command('db', MigrateCommand)


@manager.command
def sync_soundcloud():
    soundcloud.sync()

if __name__ == '__main__':
    manager.run()
