from __future__ import with_statement
from fabdefs import *
from fabric.api import *
from contextlib import contextmanager


@contextmanager
def virtualenv():
    with cd(env.project_dir):
        with prefix(env.activate):
            yield


def upload_db():
    # tar the database file
    local('tar -czf tmp.tar.gz instance/tmp.db', capture=False)
    put('tmp.tar.gz', '/tmp/tmp.tar.gz')

    # enter application directory
    with cd(env.project_dir):
        # and unzip new files
        sudo('tar xzf /tmp/tmp.tar.gz')

    # now that all is set up, delete the tarballs again
    sudo('rm /tmp/tmp.tar.gz')
    local('rm tmp.tar.gz')

    set_permissions()
    restart()
    return


def download_db():
    tmp = get('%s/instance/tmp.db' % env.project_dir, '/tmp/tmp.db')
    if tmp.succeeded:
        print "Success"
        local('mv /tmp/tmp.db instance/tmp.db')
    return

def rebuild_db():
    sudo("supervisorctl stop pmg_cms")
    with virtualenv():
        sudo('newrelic-admin run-program python %s/rebuild_db.py' % env.project_dir)
        sudo("supervisorctl start pmg_cms")

def copy_db():
    local("pg_dump -dpmg -Upmg --clean --no-owner --no-privileges > pmg.sql")
    local("tar cvzf pmg.sql.tar.gz pmg.sql")
    put('pmg.sql.tar.gz', '/tmp/pmg.sql.tar.gz')
    sudo('tar xvzf /tmp/pmg.sql.tar.gz')
    sudo('psql -dpmg -f pmg.sql', user="postgres")
    local('rm pmg.sql')
    # local('rm pmg.sql.tar.gz')
    sudo('rm /tmp/pmg.sql.tar.gz')
    sudo('rm pmg.sql')


def setup_db():
    sudo("createuser pmg -S -D -R -e", user="postgres")
    sudo("createdb --locale=en_US.utf-8 -E utf-8 -O pmg pmg -T template0", user="postgres")
    rebuild_db()
    # sudo('echo "grant all privileges on database pmg to pmg;" | psql')


def restart():
    sudo("supervisorctl restart pmg_cms")
    sudo("supervisorctl restart pmg_frontend")
    sudo('service nginx restart')
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

    with settings(warn_only=True):
        sudo('service nginx stop')

    # enter application directory and pull latest code from github
    with cd(env.project_dir):
        # ensure we are on the target branch
        sudo('git checkout ' + env.git_branch)
        # move db out of the way
        # with settings(warn_only=True):
            # sudo('mv instance/tmp.db /tmp/tmp.db')
        # first, discard local changes, then pull
        with settings(warn_only=True):
            # sudo('git stash')
            sudo('git reset --hard')
        sudo('git pull origin ' + env.git_branch)
        # put db back
        # sudo('mv /tmp/tmp.db instance/tmp.db')
        # sudo('git stash pop')

    # install dependencies
    with virtualenv():
        sudo('pip install -r %s/requirements/production.txt' % env.project_dir)

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


def restart_drupal():
    sudo("supervisorctl restart pmg_drupal")
    return



def configure_drupal():
    """
    Configure Nginx, supervisor & Flask. Then restart.
    """

    # upload nginx server blocks
    put(env.config_dir + '/nginx.conf', '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf %s/nginx_pmg_cms.conf' % env.project_dir)

    # link server blocks to Nginx config
    with settings(warn_only=True):
        sudo('ln -s %s/nginx_pmg_cms.conf /etc/nginx/conf.d/' % env.project_dir)

    # upload supervisor config
    put(env.config_dir + '/supervisor.conf', '/tmp/supervisor.conf')
    sudo('mv /tmp/supervisor.conf /etc/supervisor/conf.d/supervisor_pmg_cms.conf')
    sudo('supervisorctl reread')
    sudo('supervisorctl update')

    # configure Flask
    with settings(warn_only=True):
        sudo('mkdir %s/instance' % env.project_dir)
    put(env.config_dir + '/config_drupal.py', '/tmp/config_drupal.py')
    sudo('mv /tmp/config_drupal.py ' + env.project_dir + '/instance/config_drupal.py')

    restart_drupal()
    return


def deploy_drupal():
    # create a tarball of our packages
    local('tar -czf backend_drupal.tar.gz backend_drupal/', capture=False)

    # upload the source tarballs to the server
    put('backend_drupal.tar.gz', '/tmp/backend_drupal.tar.gz')

    # enter application directory
    with cd(env.project_dir):
        # and unzip new files
        sudo('tar xzf /tmp/backend_drupal.tar.gz')

    # now that all is set up, delete the tarballs again
    sudo('rm /tmp/backend_drupal.tar.gz')
    local('rm backend_drupal.tar.gz')

    set_permissions()
    restart_drupal()
    return
