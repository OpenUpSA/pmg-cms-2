import requests
from requests.auth import HTTPBasicAuth
from requests import ConnectionError
import simplejson as json


def pretty_print_POST(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in
    this function because it is programmed to be pretty
    printed and may differ from the actual request.
    """
    print('{}\n{}\n{}\n\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))


class Popit(object):

    def __init__(self, api_base_url=None, user=None, password=None):
        self.api_base_url = api_base_url
        self.user = user
        self.password = password
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get(self, resource_name, resource_id=None):
        query_url = self.api_base_url + resource_name + "/"
        if resource_id:
            query_url += str(resource_id) + "/"
        print query_url
        response = requests.get(query_url, headers=self.headers)
        print response.status_code
        return response.json()

    def post(self, resource_name, resource_dict):
        query_url = self.api_base_url + resource_name + "/"
        data = json.dumps(resource_dict)
        print query_url
        # req = requests.Request('POST', query_url, data=data, headers=self.headers, auth=HTTPBasicAuth(self.user, self.password))
        # prepared = req.prepare()
        # pretty_print_POST(prepared)
        # s = requests.Session()
        # response = s.send(prepared)
        response = requests.post(query_url, data=data, headers=self.headers, auth=HTTPBasicAuth(self.user, self.password))
        print json.dumps(response.headers, indent=4)
        print response.status_code
        return response.json()

    def put(self, resource_name, resource_id, resource_dict):
        query_url = self.api_base_url + resource_name + "/" + str(resource_id)
        data = json.dumps(resource_dict)
        print query_url
        response = requests.put(query_url, data=data, headers=self.headers, auth=HTTPBasicAuth(self.user, self.password))
        print response.status_code
        return response.json()

    def delete(self, resource_name, resource_id):
        query_url = self.api_base_url + resource_name + "/" + str(resource_id)
        print query_url
        response = requests.delete(query_url, headers=self.headers, auth=HTTPBasicAuth(self.user, self.password))
        print response.status_code
        if response.content:
            return response.json()
        else:
            return


if __name__ == "__main__":

    user = ""
    password = ""
    api_base_url = "http://test-pmg-za.popit.mysociety.org/api/v0.1/"

    popit = Popit(api_base_url, user, password)

    r = popit.get('persons')
    people = r['result']
    print json.dumps(people, indent=4) + "\n"

    new_guy = { "name": "John Smith" }
    r = popit.post('persons', new_guy)
    new_guy = r['result']
    print json.dumps(new_guy, indent=4) + "\n"

    new_guy['name'] = "John Smith updated"
    r = popit.put('persons', new_guy['id'], new_guy)
    new_guy = r['result']
    print json.dumps(new_guy, indent=4) + "\n"

    r = popit.delete('persons', new_guy['id'])
    print r

    r = popit.get('persons')
    people = r['result']
    print json.dumps(people, indent=4) + "\n"