from pmg import app
from flask.ext.script import Server, Manager
from flask.ext.migrate import MigrateCommand

manager = Manager(app)
manager.add_command('runserver', Server(port=5000, threaded=True))
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
