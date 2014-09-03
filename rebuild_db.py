import os
import json
import time
from backend.app import app, db
from backend.models import *

STATIC_HOST = app.config['STATIC_HOST']


def strip_filpath(filepath):

    return "/".join(filepath.split("/")[1::])


def dump_db(name):
    try:
        os.remove(name)
    except Exception as e:
        print e
        pass
    return


def read_data(filename):
    start = time.time()

    print "reading " + filename
    with open('data/' + filename, 'r') as f:
        records = []
        lines = f.readlines()
        for line in lines:
            records.append(json.loads(line))
    return records


def rebuild_db(db_name):
    """
    Save json fixtures into a structured database, intended for use in our app.
    """

    dump_db(db_name)
    db.create_all()

    start = time.time()

    # populate committee members
    members = read_data('pmg_committee_member.json')
    for member in members:
        member_obj = Member(
            name=member['title'].strip(),
            version=0
        )
        if member.get('files'):
            print json.dumps(member['files'], indent=4)
            member_obj.profile_pic_url = STATIC_HOST + strip_filpath(member["files"][-1]['filepath'])
        print member_obj.name
        print member_obj.profile_pic_url
        db.session.add(member_obj)
    db.session.commit()
    return


if __name__ == '__main__':

    rebuild_db('instance/tmp.db')