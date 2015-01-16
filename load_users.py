import json
from backend.app import app, db
from backend.models import *

with open('data/users.json', 'r') as f:
    user_list = []
    for line in f.readlines():
        user_list.append(json.loads(line))


with open('data/user_organisation.json', 'r') as f:
    org_list = []
    for line in f.readlines():
        org_list.append(json.loads(line))


if __name__ == '__main__':
    #
    # print len(user_list), "users"
    # print json.dumps(user_list[5], indent=4)
    # print json.dumps(user_list[500], indent=4)
    # print json.dumps(user_list[-1], indent=4)

    print len(org_list), "organisations"
    print json.dumps(org_list[5], indent=4)
    print json.dumps(org_list[50], indent=4)
    print json.dumps(org_list[-1], indent=4)

    # # load organisations into db
    # domain_map = {}
    # for org in org_list:
    #     # populate org model
    #     print org.get('domain')
    #     domain_map[org['domain']] = org
    #     # # set committee access subscriptions
    #     # if org.get('terms'):
    #     #     for item in org['terms']:
    #     #         print "\t", item['name']
    #
    # # load users
    # for user in user_list:
    #     # populate user model
    #     print user.get('mail'), "[" + user.get('name') + "]"
    #     # link user to organisation
    #     user_domain = user['mail'].split("@")[-1]
    #     if domain_map.get(user_domain):
    #         print "\tbelongs to", domain_map[user_domain]["name"]
    #     # # set notification subscriptions
    #     # if user.get('subscribed'):
    #     #     for item in user['subscribed']:
    #     #         print "\t", item['name']
