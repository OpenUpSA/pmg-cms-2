from pyelasticsearch import ElasticSearch
from datetime import datetime
import requests

from flask import Flask

import sys
from transforms import *

import argparse
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config.from_pyfile('./config.py')

class Search:
	# apiserver = "http://localhost:5001"
	# esserver = "http://localhost:9200"
	apiserver = app.config['API_HOST']
	# esserver = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
	esserver = app.config['ES_SERVER']
	index_name = "pmg"
	search_fields = ["title^3", "description^2", "fulltext"]
	es = ElasticSearch(esserver)
	

	def _get_all_endpoint_data(self, endpoint, data_type):
		print "Getting list %s" % endpoint
		endpoint = requests.get(endpoint);
		if (endpoint.status_code != 200):
			print "Error fetching page from api server, http error code", endpoint.status_code
			return
		data = endpoint.json()
		if not data["count"]:
			print "No results found for %s" % data_type
			return True
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
		rules = Transforms.convert_rules[data_type]
		results = []
		for doc in docs:
			tmp = {}
			# print doc
			for key, val in rules.iteritems():
				if (type(val) is list):
					formatted_val = self.getFromDict(doc, val)
				else:
					formatted_val = doc[val]
				if (type(formatted_val) is unicode) or (type(formatted_val) is str):
					formatted_val = BeautifulSoup(formatted_val).get_text().encode('utf-8').strip()
				tmp[key] = formatted_val	
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
		try:
			print "Dropping %s index" % data_type
			self.drop(data_type)
			print "Dropped %s index" % data_type
		except:
			print "Couldn't find %s index" % data_type
			pass
		# self.mapping(data_type)
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

	def mapping(self, data_type):
		mapping = {
			"properties": {
				"title": {
					"type":          "string",
					"analyzer":      "english",
					"index_options": "offsets"
				},
				"fulltext": {
					"type":          "string",
					"analyzer":      "english",
					"index_options": "offsets"
				},
				"description": {
					"type":          "string",
					"analyzer":      "english",
					"index_options": "offsets"
				}
			}
		}
		self.es.put_mapping(self.index_name, data_type, mapping)


	def search(self, query, size=10, es_from=0, start_date=False, end_date=False, content_type=False):
		q = {
			"from": es_from,
			"size": size,
			"query": {
				"filtered": {
					"filter": {},
					"query": {}
				},
			},
		}
		q["query"]["filtered"]["query"] = {
			"multi_match": {
				"query": query,
				"fields": self.search_fields,
				"type": "phrase"
			},
		}
		if start_date and end_date:
			q["query"]["filtered"]["filter"]["range"] = {
				"date": {
					"gte": start_date,
					"lte": end_date,
				}
			}
			
		q["highlight"] = {
			"pre_tags" : ["<strong>"],
			"post_tags" : ["</strong>"],
			"fields": {
				"title": {},
				"description": {"fragment_size" : 150, "number_of_fragments" : 1, "no_match_size": 150, "tag_schema" : "styled"},
				"fulltext": {"fragment_size" : 150, "number_of_fragments" : 1, "no_match_size": 150, "tag_schema" : "styled"}
			}
		}
		print "query_statement", q
		if (content_type):
			return self.es.search(q, index=self.index_name, doc_type = content_type)
		else:
			return self.es.search(q, index=self.index_name)

	def count(self, query, content_type=False, start_date=False, end_date=False):
		q1 = { 
			"query": {
					"multi_match": {
						"query": query,
						"fields": self.search_fields,
						"type": "phrase"
					},
				},
				"aggregations": {
					"types": {
						"terms": {
							"field": "_type"
						}
					}
				}
			}
		q2 = { 
			"query": {
					"multi_match": {
						"query": query,
						"fields": self.search_fields,
						"type": "phrase"
					},
				},
				"aggregations": {
					"years": {
						"date_histogram": {
							"field": "date",
							"interval": "year"
						}
					}
				}
			}
		return [self.es.search(q1, index=self.index_name, size=0), self.es.search(q2, index=self.index_name, size=0)]
	

	def import_all(self):
		for data_type in Transforms.data_types:
			self.import_data(data_type)

if (__name__ == "__main__"):
	# print "ElasticSearch PMG library"
	parser = argparse.ArgumentParser(description='ElasticSearch PMG library')
	parser.add_argument('--import',
		dest='import_data_type',
		choices = Transforms.data_types,
		help='Imports the data from a content type to ElasticSearch')
	parser.add_argument('--test', action="store_true")
	parser.add_argument('--reindex', action="store_true")
	args = parser.parse_args()
	search = Search()
	if (args.test):
		search.test()
	if (args.import_data_type):
		search.import_data(args.import_data_type)
	if (args.reindex):
		search.import_all()
	# parser.print_help()