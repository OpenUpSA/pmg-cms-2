from __future__ import division
from builtins import str
from builtins import object
from past.utils import old_div
import boto
import boto.s3
from boto.s3.key import Key
import boto.s3.connection
import math
import os
import logging

from pmg import app

S3_BUCKET = app.config['S3_BUCKET']
CACHE_SECS = 3600 * 24

logger = logging.getLogger(__name__)


def rounded_megabytes(bytes):

    megabytes = bytes / float(1024 * 1024)
    megabytes = old_div(math.ceil(megabytes * 1000), 1000)  # round the float
    return megabytes


def increment_filename(filename):
    """
    Increment a counter on the filename, so that duplicate filenames can be avoided.
    We do this by adding a counter as a path component at the start of the filename,
    so that the original name is not changed.
    """
    if '/' not in filename:
        counter = 0
        rest = filename
    else:
        counter, rest = filename.split('/', 1)
        try:
            counter = int(counter)
        except ValueError:
            # eg. foo/bar.pdf -> 1/foo/bar.pdf
            counter = 0
            rest = filename

    return '%d/%s' % (counter + 1, rest)


class S3Bucket(object):
    def __init__(self):
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            conn = boto.s3.connect_to_region('eu-west-1')
            self._bucket = conn.get_bucket(S3_BUCKET)
        return self._bucket

    def upload_file(self, path, key):
        try:
            # assemble key
            bytes = os.path.getsize(path)
            megabytes = rounded_megabytes(bytes)

            # ensure we've got a unique key
            tmp_key = self.bucket.get_key(key)
            while tmp_key is not None:
                key = increment_filename(key)
                tmp_key = self.bucket.get_key(key)

            headers = {'Cache-Control': 'max-age=%d, public' % CACHE_SECS}
            logger.debug("uploading " + path + " (" + str(megabytes) + " MB) to S3 at " + key)

            # only upload if the key doesn't exist yet
            tmp_key = Key(self.bucket)
            tmp_key.key = key
            tmp_key.set_contents_from_filename(path, headers)

        except Exception as e:
            logger.error("Cannot upload file to S3. Removing file from disk.")
            # remove file from disc
            os.remove(path)
            raise e

        # remove file from disc
        os.remove(path)
        return key
