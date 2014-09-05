import os
import json
import time
from backend_drupal.models import generate_models

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///instance/tmp_drupal.db')
Session = sessionmaker(bind=engine)
session = Session()


def dump_db():
    try:
        os.remove('instance/tmp_drupal.db')
    except Exception:
        pass
    return

def read_data():
    start = time.time()
    files = os.listdir('data')
    data = {}

    for file in files:
        print "reading " + file
        with open('data/' + file, 'r') as f:
            records = []
            lines = f.readlines()
            for line in lines:
                records.append(json.loads(line))
            example = records[0]
            data[file[4:-5]] = records
    print str(int(time.time() - start)) + " seconds, ready"
    return data


def move_to_front(entry, entry_list):

    if entry in entry_list:
        i = entry_list.index(entry)
        entry_list = [entry,] + entry_list[0:i] + entry_list[i+1::]
    return entry_list


def print_model_defs():

    data = read_data()
    model_names = data.keys()
    model_names.sort()

    field_order = [u'start_date', u'title', u'minutes', u'files', u'meeting_date', u'terms', u'audio', u'version', u'revisions']
    field_order.reverse()

    for name in model_names:
        fields = data[name][0].keys()
        fields.sort()
        for field_name in field_order:
            fields = move_to_front(field_name, fields)

        print "('" + name + "', " + str(fields) + "),"
    return


def populate_db(model, records):

    for rec in records:
        tmp = model()
        fields = rec.keys()
        fields.sort()
        for field in fields:
            if rec[field]:
                if type(rec[field]=='dict'):
                    val = json.dumps(rec[field]).encode('utf-8').strip()
                else:
                    val = rec[field].encode('utf-8').strip()
                setattr(tmp, field, val)
        session.add(tmp)
    return


if __name__ == '__main__':

    # print_model_defs()

    dump_db()

    data = read_data()
    model_dict = generate_models()
    print model_dict

    start = time.time()

    model_names = model_dict.keys()
    model_names.sort()

    for name in model_names:
        print name
        populate_db(model_dict[name], data[name])
        session.commit()
        print str(int(time.time() - start)) + " seconds"