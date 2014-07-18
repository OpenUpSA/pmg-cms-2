import os
import json
import time
from backend.database import session
import backend.models as models


def dump_db():
    try:
        os.remove('instance/tmp.db')
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


def print_model_defs(data):

    model_names = data.keys()
    model_names.sort()

    for name in model_names:
        fields = data[name][0].keys()
        fields.sort()
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

    dump_db()

    data = read_data()
    model_dict = models.generate_models()
    print model_dict

    start = time.time()

    model_names = model_dict.keys()
    model_names.sort()

    for name in model_names:
        print name
        populate_db(model_dict[name], data[name][0:99])
        session.commit()
        print str(int(time.time() - start)) + " seconds"