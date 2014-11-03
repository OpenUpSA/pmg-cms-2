from pyelasticsearch import ElasticSearch
from datetime import datetime
import requests


class Search:
	# apiserver = "http://localhost:5001"
	# esserver = "http://localhost:9200"
	apiserver = "http://pmg-cms.demo4sa.org"
	esserver = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
	index_name = "pmg"
	search_fields = ["name", "title"]
	es = ElasticSearch(esserver)
	convert_rules = {
		"committee": {
			"id": "id",
			"title": "name",
			"description": ["info", "about"]
		},
		"committee-meeting": {
			"id": "id",
			"title": "title",
			"description": ["content", 0, "summary"],
			"fulltext": ["content", 0, "body"]
		},
		"member": {
			"id": "id",
			"title": "name",
			"description": "bio"
		}
	}

	def _get_all_endpoint_data(self, endpoint, data_type):
		endpoint = requests.get(endpoint);
		if (endpoint.status_code != 200):
			print "Error fetching page from api server, http error code", endpoint.status_code
			return
		data = endpoint.json()
		docs = data["results"]
		docs = self._import_content(data_type, docs)
		docs = self._format_data(data_type, docs)
		print "Indexing", len(docs), "items"
		self.es.bulk_index(self.index_name, data_type, docs)
		if (data["next"]):
			self._get_all_endpoint_data(data["next"], data_type)
		return True

	def getFromDict(self, dataDict, mapList):
		return reduce(lambda d, k: d[k], mapList, dataDict)

	def _format_data(self, data_type, docs):
		rules = self.convert_rules[data_type]
		results = []
		for doc in docs:
			tmp = {}
			# print doc
			for key, val in rules.iteritems():
				if (type(val) is list):
					tmp[key] = self.getFromDict(doc, val)
				else:
					tmp[key] = doc[val]
			results.append(tmp)
		return results

	def test(self):
		print "Test Insert"
		self.insert("test-type", { "id": 1, "name": "Hello Dolly!", "Foo": "Bar", "Bar": "Yack", "timestamp": datetime.now() })
		# es.index("test", "test-type", { "Foo": "Bar", "Bar": "Yack", "timestamp": datetime.now() }, 1)
		doc = self.get("test-type", 1)
		# doc = es.get("test", "test-type", 1)
		if (doc):
			if (doc["_source"]["Foo"] == "Bar"):
				print "Test Passed"
			else:
				print "Test Failed"
		else:
			print "Test Failed"
		print "Test Search"
		doc = self.search("hello dolly")["hits"]["hits"][0]
		if (doc):
			if (doc["_source"]["Foo"] == "Bar"):
				print "Test Passed"
			else:
				print "Test Failed"
		else:
			print "Test Failed"
		print "Test Delete"
		self.delete("test-type", 1)
		doc = self.get("test-type", 1)
		if not doc:
			print "Test Passed"
		else:
			print "Test Failed"


	# Gets a list of the content, but doesn't go deep
	def import_data(self, data_type):
		docs = []
		docs = self._get_all_endpoint_data(self.apiserver + "/" + data_type + "/", data_type)
		# print docs
		# docs = self._import_content(data_type, docs)
		# docs = self._format_data(data_type, docs)
		# print docs
		# print "Indexing", len(docs), "items"
		# self.es.bulk_index(self.index_name, data_type, docs)

	# Gets more content on each item
	def _import_content(self, data_type, docs):
		result = []
		for doc in docs:
			print "Getting", self.apiserver + "/" + data_type + "/" + str(doc["id"])
			response = requests.get(self.apiserver + "/" + data_type + "/" + str(doc["id"]))
			if (response.status_code == 200):
				result.append(response.json())
			else:
				print "HTTP error %d" % response.status_code
		return result
		# print docs

	def drop(self, data_type):
		self.es.delete_all(self.index_name, data_type)

	def update(self, data_type, item, uid = False):
		if not uid:
			if (item["id"]):
				uid = item["id"]
		self.es.index(self.index_name, data_type, item, uid)

	def insert(self, data_type, item, uid = False):
		if not uid:
			if (item["id"]):
				uid = item["id"]
		self.es.index(self.index_name, data_type, item, uid)

	def delete(self, data_type, uid):
		self.es.delete(self.index_name, data_type, uid)

	def get(self, data_type, uid):
		try:
			return self.es.get(self.index_name, data_type, uid)
		except:
			return False

	def search(self, query, size=10, es_from=0):
		q = {
			"from": es_from,
			"size": size,
			"query": {
				"multi_match": {
					"query": query,
					"fields": self.search_fields
				}
			}
		}
		return self.es.search(q, index=self.index_name)


if (__name__ == "__main__"):
	print "ElasticSearch PMG library"