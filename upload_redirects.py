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
for redirect in existing_redirects:
    old_urls.append(redirect.old_url)

error_count = 0

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
        if nid and not url in old_urls:
            redirect = Redirect(nid=nid, old_url=url)
            old_urls.append(url)
            db.session.add(redirect)
        else:
            error_count += 1
            print nid, redirects[i]['url'].encode('utf8')
    if i % 500 == 0:
        print "saving 500 redirects (" + str(i) + " out of " + str(len(redirects)) + ")"
        db.session.commit()
db.session.commit()

print "Error count:", str(error_count)