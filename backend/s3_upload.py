import boto
import boto.s3
from boto.s3.key import Key
import boto.s3.connection
import math
import os
from app import db, app
import logging

UPLOAD_PATH = app.config['UPLOAD_PATH']
S3_BUCKET = app.config['S3_BUCKET']

logger = logging.getLogger(__name__)


def rounded_megabytes(bytes):

    megabytes = bytes/float(1024*1024)
    megabytes = math.ceil(megabytes*1000)/1000  # round the float
    return megabytes


class S3Bucket():

    def __init__(self):
        self.bucket = None
        return

    def get_bucket(self):

        conn = boto.s3.connect_to_region('eu-west-1')
        self.bucket = conn.get_bucket(S3_BUCKET)
        return

    def upload_file(self, filename):

        try:
            if not self.bucket:
                self.get_bucket()
            # assemble key
            path = os.path.join(UPLOAD_PATH, filename)
            bytes = os.path.getsize(path)
            megabytes = rounded_megabytes(bytes)
            logger.debug("uploading: " + path + " (" + str(megabytes) + " MB)")

            # test if the key already exists
            tmp_key = self.bucket.get_key(filename)
            if tmp_key is not None:
                raise ValueError("file already uploaded")
            else:
                # only upload if the key doesn't exist yet
                tmp_key = Key(self.bucket)
                tmp_key.key = filename
                tmp_key.set_contents_from_filename(path)

        except Exception as e:
            logger.error("Cannot upload file to S3. Removing file from disc.")
            # remove file from disc
            os.remove(filename)
            raise e

        # remove file from disc
        os.remove(filename)
        return


if __name__ == "__main__":

    filename = "/Users/petrus/Desktop/5-elephant.jpg"
    tmp = S3Bucket()
    tmp.upload_file(filename)
