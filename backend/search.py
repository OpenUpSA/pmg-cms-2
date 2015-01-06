from pyelasticsearch import ElasticSearch
from datetime import datetime
import requests
from app import db, app
from flask import Flask
import models
from sqlalchemy import types
import sys
from transforms import *
import math
import argparse
from bs4 import BeautifulSoup
import logging
from functools import reduce


class Search:

    esserver = app.config['ES_SERVER']
    index_name = "pmg"
    search_fields = ["title^3", "description^2", "fulltext"]
    es = ElasticSearch(esserver)
    per_batch = 50
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    def _getVal(self, obj, field):
        if isinstance(field, list):
            if (len(field) == 1):
                if hasattr(obj, field[0]):
                    return getattr(obj, field[0])
            key = field[:1][0]
            if isinstance(key, int):
                if len(obj) > key:
                    return self._getVal(obj[key], field[1:])
                return None
            if hasattr(obj, key):
                newobj = getattr(obj, key)
                return self._getVal(newobj, field[1:])
            else:
                return None
        else:
            return getattr(obj, field)

    def _get_all_data(self, data_type):
        Model = getattr(models, Transforms.model_model[data_type])
        ids = []
        for row in db.session.query(Model.id).all():
            ids.append(row.id)
        count = len(ids)
        pages = int(math.ceil(float(count) / float(self.per_batch)))
        print "Pages", pages, "Count", count
        while len(ids):
            print "Items left", len(ids)
            id_subsection = []
            for x in range(0, self.per_batch):
                if ids:
                    id_subsection.append(ids.pop())
            items = []
            for row in db.session.query(Model).filter(
                    Model.id.in_(id_subsection)).all():
                item = {}
                for key, field in Transforms.convert_rules[
                        data_type].iteritems():
                    val = self._getVal(row, field)
                    # self.logger.debug(key)
                    # self.logger.debug(row.committee[0].name)

                    if isinstance(val, unicode):
                        val = BeautifulSoup(val).get_text().strip()
                    # print key, val[:20].encode("utf-8")
                    # else:
                    # print key, val
                    item[key] = val
                # return
                items.append(item)
            self.es.bulk_index(self.index_name, data_type, items)
            # self.insert(data_type, item)

    def getFromDict(self, dataDict, mapList):
        return reduce(lambda d, k: d[k], mapList, dataDict)

    def test(self):
        print "Test Insert"
        self.insert("test-type",
                    {"id": 1,
                     "name": "Hello Dolly!",
                     "Foo": "Bar",
                     "Bar": "Yack",
                     "timestamp": datetime.now()})
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

    # Imports all content of a data_type
    def import_data(self, data_type):
        docs = []
        try:
            print "Dropping %s index" % data_type
            self.drop(data_type)
            print "Dropped %s index" % data_type
        except:
            print "Couldn't find %s index" % data_type
            pass
        self._get_all_data(data_type)

    # Gets more content on each item
    def _import_content(self, data_type, docs):
        result = []
        for doc in docs:
            print "Getting", self.apiserver + "/" + data_type + "/" + str(doc["id"])
            response = requests.get(self.apiserver +
                                    "/" +
                                    data_type +
                                    "/" +
                                    str(doc["id"]))
            if (response.status_code == 200):
                result.append(response.json())
            else:
                print "HTTP error %d" % response.status_code
        return result
    # print docs

    def drop(self, data_type):
        self.es.delete_all(self.index_name, data_type)

    def update(self, data_type, item, uid=False):
        if not uid:
            if (item["id"]):
                uid = item["id"]
        self.es.index(self.index_name, data_type, item, uid)

    def insert(self, data_type, item, uid=False):
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
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                },
                "fulltext": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                },
                "description": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                }
            }
        }
        self.es.put_mapping(self.index_name, data_type, mapping)

    def search(
            self,
            query,
            size=10,
            es_from=0,
            start_date=False,
            end_date=False,
            content_type=False,
            committee=False):
        q = {
            "from": es_from,
            "size": size,
            "query": {
                "filtered": {
                    "filter": {},
                    "query": {},
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
        if committee:
            q["query"]["filtered"]["filter"]["term"] = {
                "committee_id": committee
            }

        q["highlight"] = {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "title": {},
                "description": {
                    "fragment_size": 500,
                    "number_of_fragments": 1,
                    "no_match_size": 250,
                    "tag_schema": "styled"},
                "fulltext": {
                    "fragment_size": 500,
                    "number_of_fragments": 1,
                    "no_match_size": 250,
                    "tag_schema": "styled"}}}
        print "query_statement", q
        if (content_type):
            return self.es.search(
                q,
                index=self.index_name,
                doc_type=content_type)
        else:
            return self.es.search(q, index=self.index_name)

    def count(
            self,
            query,
            content_type=False,
            start_date=False,
            end_date=False):
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
        return [
            self.es.search(
                q1,
                index=self.index_name,
                size=0),
            self.es.search(
                q2,
                index=self.index_name,
                size=0)]

    def import_all(self):
        for data_type in Transforms.data_types:
            self.import_data(data_type)


if __name__ == "__main__":
    # print "ElasticSearch PMG library"
    parser = argparse.ArgumentParser(description='ElasticSearch PMG library')
    parser.add_argument(
        '--import',
        dest='import_data_type',
        choices=Transforms.data_types,
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
