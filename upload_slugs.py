import json
from backend.app import app, db
from backend.models import *
from flask import url_for

# read in json redirect dump
with open('data/nid_url.json', 'r') as f:

    redirects = json.loads(f.read())

print len(redirects)

old_urls = []

existing_redirects = Redirect.query.all()
for tmp in existing_redirects:
    old_urls.append(tmp.old_url)

error_count = 0
no_nid_count = 0
duplicate_count = 0

for i in range(len(redirects)):
    nid = None
    try:
        nid = int(redirects[i]['nid'])
    except ValueError as e:
        tmp = redirects[i]['nid']
        if not 'user' in tmp:
            tmp = tmp.split('/')
            for item in tmp:
                try:
                    nid = int(item)
                    break
                except ValueError:
                    pass
    url = redirects[i]['url']
    if not nid:
        no_nid_count += 1
    elif url in old_urls:
        duplicate_count += 1

    else:
        redirect = Redirect(nid=nid, old_url=url)
        old_urls.append(url)
        db.session.add(redirect)
        # print nid, redirects[i]['url'].encode('utf8')
    if i % 500 == 0:
        print "saving 500 redirects (" + str(i) + " out of " + str(len(redirects)) + ")"
        db.session.commit()
db.session.commit()

print duplicate_count, "duplicates found"
print no_nid_count, "nids could not be parsed"