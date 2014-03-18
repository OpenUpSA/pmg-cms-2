from fabric.api import *

"""
Define the server environments that this app will be deployed to.
Ensure that you have SSH access to the servers for the scripts in 'fabfile.py' to work.
"""


def staging():
    """
    Env parameters for the staging environment.
    """

    env.hosts = ["user@server:port"]
    env.project_dir = '/var/www/project-template'  # the directory where the application resides on the server
    env.config_dir = 'config/staging'  # the local directory where the config files for this server is kept
    env.env_dir = env.project_dir + "/env"  # path to this app's virtualenv (important if it runs on a shared server)
    return


def production():
    """
    Env parameters for the production environment.
    """

    env.hosts = ["user@server:port"]
    env.project_dir = '/var/www/project-template'  # the directory where the application resides on the server
    env.config_dir = 'config/production'  # the local directory where the config files for this server is kept
    env.env_dir = env.project_dir + "/env"  # path to this app's virtualenv (important if it runs on a shared server)
    return