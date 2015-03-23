import boto
import boto.s3
from boto.s3.key import Key
import boto.s3.connection
import math
import os
import logging

from pmg import db, app

UPLOAD_PATH = app.config['UPLOAD_PATH']
S3_BUCKET = app.config['S3_BUCKET']

logger = logging.getLogger(__name__)


def rounded_megabytes(bytes):

    megabytes = bytes / float(1024 * 1024)
    megabytes = math.ceil(megabytes * 1000) / 1000  # round the float
    return megabytes


def increment_filename(duplicate_filename):
    """
    Increment a counter on the filename, so that duplicate filenames can be avoided.
    """
    tmp = duplicate_filename.split(".")
    filename, extension = ".".join(tmp[0:-1]), tmp[-1]
    try:
        tmp2 = filename.split("_")
        count = int(tmp2[-1])
        count += 1
        tmp2[-1] = str(count)
        filename = "_".join(tmp2)
    except ValueError as e:
        filename += "_2"
        pass
    return filename + "." + extension


class S3Bucket():

    def __init__(self):
        self.bucket = None
        return

    def get_bucket(self):

        conn = boto.s3.connect_to_region('eu-west-1')
        self.bucket = conn.get_bucket(S3_BUCKET)
        return

    def upload_file(self, filename):

        path = os.path.join(UPLOAD_PATH, filename)
        try:
            if not self.bucket:
                self.get_bucket()
            # assemble key
            bytes = os.path.getsize(path)
            megabytes = rounded_megabytes(bytes)
            logger.debug("uploading: " + path + " (" + str(megabytes) + " MB)")

            # ensure we've got a unique key
            tmp_key = self.bucket.get_key(filename)
            while tmp_key is not None:
                filename = increment_filename(filename)
                tmp_key = self.bucket.get_key(filename)

            # only upload if the key doesn't exist yet
            tmp_key = Key(self.bucket)
            tmp_key.key = filename
            tmp_key.set_contents_from_filename(path)

        except Exception as e:
            logger.error("Cannot upload file to S3. Removing file from disc.")
            # remove file from disc
            os.remove(path)
            raise e

        # remove file from disc
        os.remove(path)
        return filename


if __name__ == "__main__":

    filename = "5.elephant.jpg"  # a sample file, inside UPLOAD_PATH directory
    for i in range(5):
        filename = increment_filename(filename)
        print filename
    # tmp = S3Bucket()
    # tmp.upload_file(filename)
