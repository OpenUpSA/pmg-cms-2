from __future__ import with_statement
from fabdefs import *
from fabric.api import *
from contextlib import contextmanager

# hook for activating a virtualenv on the server
env.activate = 'source %s/env/bin/activate' % env.code_dir

@contextmanager
def virtualenv():
    with cd(env.code_dir):
        with prefix(env.activate):
            yield


def setup():

    return


def configure():

    return


def deploy():

    return