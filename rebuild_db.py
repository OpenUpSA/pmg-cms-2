import os
import json
import time

start = time.time()
files = os.listdir('data')

for file in files:
    print file
    with open('data/' + file, 'r') as f:
        records = []
        lines = f.readlines()
        for line in lines:
            records.append(json.loads(line))
        example = records[0]
        print int(time.time() - start)
        print example.keys()