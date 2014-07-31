import boto
import boto.s3
from boto.s3.key import Key
import boto.s3.connection
import datetime
import math
import os
from os.path import isfile, join


def rounded_megabytes(bytes):

    megabytes = bytes/float(1024*1024)
    megabytes = math.ceil(megabytes*1000)/1000  # round the float
    return megabytes


def get_file_size(directory_path, filename):

    bytes = os.path.getsize(directory_path + filename)
    return bytes


def get_bucket(bucket_name):

    conn = boto.connect_s3()
    bucket = conn.get_bucket(bucket_name)
    return bucket


def upload_file(bucket, filename, directory_path):

    bytes = get_file_size(directory_path, filename)
    megabytes = rounded_megabytes(bytes)
    print "uploading: " + directory_path + filename + " (" + str(megabytes) + " MB)"
    # test if the key already exists
    tmp_key = bucket.get_key(filename)
    if tmp_key is not None:
        print "  file already uploaded"
        raise ValueError, "file already uploaded"
    else:
        # only upload if the key doesn't exist yet
        tmp_key = Key(bucket)
        tmp_key.key = filename
        tmp_key.set_contents_from_filename(directory_path + filename)
    return


def download_file(bucket, filename, directory_path):

    tmp_key = Key(bucket)
    tmp_key.key = filename
    tmp_key.get_contents_to_filename(directory_path + filename)
    return


def upload_directory(bucket, directory_path):

    # assemble a list of files in the directory
    content = os.listdir(directory_path)
    file_list = []
    for item in content:
        if isfile(join(directory_path, item)):
            file_list.append(item)

    # calculate overall size to be uploaded
    total_bytes = 0
    progress = 0
    for filename in file_list:
        bytes = get_file_size(directory_path, filename)
        total_bytes += bytes

    i = 0
    start = datetime.datetime.now()
    for filename in file_list:
        bytes = get_file_size(directory_path, filename)
        try:
            upload_file(bucket, filename, directory_path)
            progress += bytes
        except ValueError:
            total_bytes -= bytes
            pass
        i += 1
        if i % 10 == 0:
            tmp = str(int(100*(progress/float(total_bytes))))
            print "\n" + str(rounded_megabytes(progress)) + " MB out of " + str(rounded_megabytes(total_bytes)) + " MB uploaded (" + tmp + "%)"
            lapsed = (datetime.datetime.now()-start).seconds
            if lapsed >= 1:
                speed = int((progress / 1024) / lapsed)
                print str(speed) + " kbps average upload speed"
                if speed >= 1:
                    seconds_remaining = int(((total_bytes - progress) / 1024) / speed)
                    hours_remaining = seconds_remaining / float(3600)
                    hours_remaining = math.ceil(hours_remaining*10)/10
                    print str(hours_remaining) + " hours remaining"
    return


if __name__ == "__main__":

    bucket = get_bucket('oregon-pmg-files')
    bucket.set_acl('public-read')
    upload_directory(bucket, "/var/www/websitedata/drupal/files/")
    # bucket = get_bucket('oregon-pmg-audio')
    # bucket.set_acl('public-read')
    # upload_directory(bucket, "/var/www/websitedata/drupal/files/audio/")
