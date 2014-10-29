from pyelasticsearch import ElasticSearch
from datetime import datetime
import requests


apiserver = "http://localhost:5001"
esserver = "http://localhost:9200"
index_name = "pmg"
search_fields = ["name", "title"]
es = ElasticSearch(esserver)

def _get_all_endpoint_data(endpoint, docs):
	endpoint = requests.get(endpoint);
	if (endpoint.status_code != 200):
		print "Error fetching page from api server, http error code", endpoint.status_code
		return
	data = endpoint.json()
	docs = docs + data["results"]
	if (data["next"]):
		docs = _get_all_endpoint_data(data["next"], docs)
	return docs

def test():
	print "Test Insert"
	insert("test-type", { "id": 1, "name": "Hello Dolly!", "Foo": "Bar", "Bar": "Yack", "timestamp": datetime.now() })
	# es.index("test", "test-type", { "Foo": "Bar", "Bar": "Yack", "timestamp": datetime.now() }, 1)
	doc = get("test-type", 1)
	# doc = es.get("test", "test-type", 1)
	if (doc):
		if (doc["_source"]["Foo"] == "Bar"):
			print "Test Passed"
		else:
			print "Test Failed"
	else:
		print "Test Failed"
	print "Test Search"
	doc = search("hello dolly")["hits"]["hits"][0]
	if (doc):
		if (doc["_source"]["Foo"] == "Bar"):
			print "Test Passed"
		else:
			print "Test Failed"
	else:
		print "Test Failed"
	print "Test Delete"
	delete("test-type", 1)
	doc = get("test-type", 1)
	if not doc:
		print "Test Passed"
	else:
		print "Test Failed"


def import_data(data_type):
	docs = []
	docs = _get_all_endpoint_data(apiserver + "/" + data_type + "/", [])
	print "Indexing", len(docs), "items"
	es.bulk_index(index_name, data_type, docs)

def drop(data_type):
	es.delete_all(index_name, data_type)

def update(data_type, item, uid = False):
	if not uid:
		if (item["id"]):
			uid = item["id"]
	es.index(index_name, data_type, item, uid)

def insert(data_type, item, uid = False):
	if not uid:
		if (item["id"]):
			uid = item["id"]
	es.index(index_name, data_type, item, uid)

def delete(data_type, uid):
	es.delete(index_name, data_type, uid)

def get(data_type, uid):
	try:
		return es.get(index_name, data_type, uid)
	except:
		return False

def search(query, size=10):
	q = {
		"query": {
			"multi_match": {
				"query": query,
				"fields": search_fields
			}
		}
	}
	return es.search(q, index=index_name, size=size)


if (__name__ == "__main__"):
	print "ElasticSearch PMG library"