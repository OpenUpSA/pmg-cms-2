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
    put('instance/tmp.db', '/tmp/tmp.db')
    with settings(warn_only=True):
        sudo("supervisorctl stop pmg_cms")
    sudo('mv /tmp/tmp.db %s/instance/tmp.db' % env.project_dir)
    set_permissions()
    restart()
    return


def download_db():
    tmp = get('%s/instance/tmp.db' % env.project_dir, '/tmp/tmp.db')
    if tmp.succeeded:
        print "Success"
        local('mv /tmp/tmp.db instance/tmp.db')
    return


def restart():
    sudo("supervisorctl restart pmg_cms")
    sudo('service nginx restart')
    return


def set_permissions():
    """
     Ensure that www-data has access to the application folder
    """

    sudo('chown -R www-data:www-data ' + env.project_dir)
    return


def setup():

    # # update locale
    # sudo('locale-gen en_ZA.UTF-8')
    sudo('apt-get update')

    # # install packages
    # sudo('apt-get install build-essential')
    # sudo('apt-get install python-pip supervisor')
    # sudo('pip install virtualenv')
    sudo('apt-get install git')

    # create application directory if it doesn't exist yet
    with settings(warn_only=True):
        if run("test -d %s" % env.project_dir).failed:
            # create project folder
            sudo("git clone https://github.com/Code4SA/pmg-cms.git " + env.project_dir)
        if run("test -d %s/env" % env.project_dir).failed:
            # create virtualenv
            sudo('virtualenv --no-site-packages %s/env' % env.project_dir)

    # install the necessary Python packages
    with virtualenv():
        put('requirements/base.txt', '/tmp/base.txt')
        put('requirements/production.txt', '/tmp/production.txt')
        sudo('pip install -r /tmp/production.txt')

    # # install nginx
    # sudo('apt-get install nginx')
    # # restart nginx after reboot
    # sudo('update-rc.d nginx defaults')
    # sudo('service nginx start')
    return


def configure():
    """
    Configure Nginx, supervisor & Flask. Then restart.
    """

    with settings(warn_only=True):
        # disable default site
        sudo('rm /etc/nginx/sites-enabled/default')

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
    put(env.config_dir + '/config.py', '/tmp/config.py')
    put(env.config_dir + '/config_private.py', '/tmp/config_private.py')
    sudo('mv /tmp/config.py ' + env.project_dir + '/instance/config.py')
    sudo('mv /tmp/config_private.py ' + env.project_dir + '/instance/config_private.py')

    restart()
    return


def deploy():
    # create a tarball of our packages
    local('tar -czf backend.tar.gz backend/', capture=False)

    # upload the source tarballs to the server
    put('backend.tar.gz', '/tmp/backend.tar.gz')

    # enter application directory
    with cd(env.project_dir):
        # and unzip new files
        sudo('tar xzf /tmp/backend.tar.gz')

    # now that all is set up, delete the tarballs again
    sudo('rm /tmp/backend.tar.gz')
    local('rm backend.tar.gz')

    set_permissions()
    restart()
    return