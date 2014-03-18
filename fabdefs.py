from fabric.api import *

"""
The server environments that this app deploys to, are defined here.
"""

env.hosts = ["user@server:port"]
code_dir = "/path/to/code/root"


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