from __future__ import with_statement
from fabdefs import *
from fabric.api import *
from contextlib import contextmanager


@contextmanager
def virtualenv():
    with cd(env.project_dir):
        with prefix(env.activate):
            yield


def setup_db():
    sudo("createuser pmg -S -D -R -e", user="postgres")
    sudo("createdb --locale=en_US.utf-8 -E utf-8 -O pmg pmg -T template0", user="postgres")


def index_search():
    with virtualenv():
        with cd('/var/www/pmg-cms'):
            run('source production-env.sh; python pmg/search.py --reindex all')

def hard_restart():
    sudo("supervisorctl restart pmg")
    return

def restart():
    sudo("kill -HUP `cat /var/www/pmg-cms/gunicorn.pid` || supervisorctl restart pmg")
    return


def set_permissions():
    """
     Ensure that www-data has access to the application folder
    """

    sudo('chown -R www-data:www-data ' + env.project_dir)
    return


def setup():

    sudo('apt-get update')

    # install packages
    sudo('apt-get -y install git')
    sudo('apt-get -y install build-essential python-dev sqlite3 libsqlite3-dev libpq-dev')
    sudo('apt-get -y install python-pip supervisor')
    sudo('pip install virtualenv')

    # create application directory if it doesn't exist yet
    with settings(warn_only=True):
        if run("test -d %s" % env.project_dir).failed:
            sudo('git clone https://github@github.com/code4sa/pmg-cms-2.git %s' % env.project_dir)
            sudo('mkdir %s/instance' % env.project_dir)
        if run("test -d %s/env" % env.project_dir).failed:
            # create virtualenv
            sudo('virtualenv --no-site-packages %s/env' % env.project_dir)

    # install nginx
    sudo('apt-get -y install nginx')
    # restart nginx after reboot
    sudo('update-rc.d nginx defaults')
    with settings(warn_only=True):
        sudo('rm /etc/nginx/sites-enabled/default')
    with settings(warn_only=True):
        sudo('service nginx start')

    # Database setup
    sudo('apt-get -y install postgresql')
    return


def deploy():
    # push any local changes to github
    local('git push origin ' + env.git_branch)

    # enter application directory and pull latest code from github
    with cd(env.project_dir):
        # first, discard local changes, then pull
        with settings(warn_only=True):
            sudo('git reset --hard')
        sudo('git pull origin ' + env.git_branch)
        # ensure we are on the target branch
        sudo('git checkout -f ' + env.git_branch)

    # install dependencies
    with virtualenv():
        sudo('pip install -r %s/requirements.txt' % env.project_dir)

    with cd(env.project_dir):
        # nginx
        sudo('ln -sf ' + env.config_dir + '/nginx.conf /etc/nginx/sites-enabled/pmg.org.za')
        sudo('service nginx reload')

        # move supervisor config
        sudo('ln -sf ' + env.config_dir + '/supervisor.conf /etc/supervisor/conf.d/supervisor_pmg.conf')
        sudo('supervisorctl reread')
        sudo('supervisorctl update')

    set_permissions()
    restart()
    return
