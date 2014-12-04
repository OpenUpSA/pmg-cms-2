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


def get_bucket(bucket_name):

    conn = boto.s3.connect_to_region('eu-west-1')
    bucket = conn.get_bucket(bucket_name)
    return bucket


def upload_file(filename):

    try:
        # assemble key
        path = os.path.join(UPLOAD_PATH, filename)
        bytes = os.path.getsize(path)
        megabytes = rounded_megabytes(bytes)
        logger.debug("uploading: " + path + " (" + str(megabytes) + " MB)")

        # test if the key already exists
        tmp_key = bucket.get_key(filename)
        if tmp_key is not None:
            raise ValueError("file already uploaded")
        else:
            # only upload if the key doesn't exist yet
            tmp_key = Key(bucket)
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

bucket = get_bucket(S3_BUCKET)


if __name__ == "__main__":

    filename = "5-leopard.jpg"
    upload_file(filename)
