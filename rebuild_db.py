import os
import json
import time
from backend.database import session
import backend.models as models


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


def create_models(data):

    model_dict = {}
   
    model_names = data.keys()
    model_names.sort()

    for name in model_names:
        print "\n" + name
        fields = data[name][0].keys()
        fields.sort()

        model_dict[name] = models.get_content_type_model(name, fields)

    return model_dict

if __name__ == '__main__':

    data = read_data()
    model_dict = create_models(data)
    print model_dict