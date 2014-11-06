from fabric.api import *

"""
Define the server environments that this app will be deployed to.
Ensure that you have SSH access to the servers for the scripts in 'fabfile.py' to work.
"""


def production():
    """
    Env parameters for the production environment.
    """

    env.host_string = 'ubuntu@54.76.117.251'
    env.project_dir = '/var/www/pmg-cms'
    env.config_dir = env.project_dir + '/config/production'
    env.git_branch = 'master'
    env.activate = 'source %s/env/bin/activate' % env.project_dir
    print("PRODUCTION ENVIRONMENT\n")
    return
