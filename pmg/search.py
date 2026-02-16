from builtins import str
from builtins import range

import math
import logging
import json
from collections import OrderedDict
import re
import copy
import pickle
import datetime

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError, ConnectionError, ConnectionTimeout
import pytz

from bs4 import BeautifulSoup

from . import db, app
from pmg.models.resources import *  # noqa
from pmg.models.posts import Post
from pmg.models.base import resource_slugs

PHRASE_RE = re.compile(r'"([^"]*)("|$)')
MAX_INDEXABLE_BYTES = 104857600  # Limit Elasticsearch/Netty has by default
ATTACHMENT_PIPELINE = "attachment_pipeline"


class Search:

    esserver = app.config["ES_SERVER"]
    index_name = "pmg"
    search_fields = ["title^2", "description", "fulltext", "attachment.content"]
    exact_search_fields = [
        "title.exact^2",
        "description.exact",
        "fulltext.exact",
        "attachment_content_exact",
    ]
    es = Elasticsearch(esserver)
    per_batch = 200
    logger = logging.getLogger(__name__)

    reindex_changes = app.config["SEARCH_REINDEX_CHANGES"]
    """ Should updates to models be reindexed? """

    friendly_data_types = OrderedDict(
        [
            ("committee", "Committees"),
            ("committee_meeting", "Committee Meetings"),
            ("bill", "Bills"),
            ("member", "MPs"),
            ("hansard", "Hansards"),
            ("briefing", "Media Briefings"),
            # this is both QuestionReply and CommitteeQuestion objects
            ("minister_question", "Questions & Replies"),
            ("tabled_committee_report", "Tabled Committee Reports"),
            ("call_for_comment", "Calls for Comments"),
            ("policy_document", "Policy Documents"),
            ("gazette", "Gazettes"),
            ("daily_schedule", "Daily Schedules"),
            ("post", "Blog Posts"),
            ("petition", "Petitions"),
        ]
    )

    def ensure_index(self):
        """Ensure the index, mapping and ingest pipeline exist.

        Safe to call repeatedly — will not error if they already exist.
        """
        try:
            if not self.es.indices.exists(index=self.index_name):
                self.create_index()
            else:
                # Ensure pipeline and mapping are up-to-date
                self.setup_attachment_pipeline()
                self.mapping()
        except Exception:
            self.logger.exception("Error ensuring index exists")
            raise

    def reindex_all(self, data_type):
        """ Index all content of a data_type """
        self.ensure_index()
        self.drop_index(data_type)
        models = [
            m
            for m in list(resource_slugs.values())
            if m.resource_content_type == data_type
        ]
        for model in models:
            self.reindex_for_model(model)

    def reindex_for_model(self, model):
        """ Index all content of type +model+ """
        ids = [r[0] for r in db.session.query(model.id).all()]

        if model.__name__ == "Bill":
            per_batch = 1
        else:
            per_batch = self.per_batch

        count = len(ids)
        pages = int(math.ceil(float(count) / float(per_batch)))
        self.logger.info("Reindexing for %s" % model.__name__)
        self.logger.info("Pages %s, %s per page, %s items" % (pages, per_batch, count))

        while len(ids):
            self.logger.info("Items left %s" % len(ids))
            id_subsection = []
            for x in range(0, per_batch):
                if ids:
                    id_subsection.append(ids.pop())

            rows = db.session.query(model).filter(model.id.in_(id_subsection)).all()
            items = [Transforms.serialise(r) for r in rows]
            items = self.filter_too_large(items)
            if items:
                self.add_many(model.resource_content_type, items)

    def filter_too_large(self, items):
        ok_items = []
        for item in items:
            size = len(pickle.dumps(item))
            if size < MAX_INDEXABLE_BYTES:
                ok_items.append(item)
            else:
                self.logger.warn(
                    "Not indexing %s id=%d bigger than max (%d > %d)",
                    item["slug_prefix"],
                    item["model_id"],
                    size,
                    MAX_INDEXABLE_BYTES,
                )
        return ok_items

    def drop_index(self, data_type):
        """Delete all documents of a given data_type from the index"""
        self.logger.info("Dropping %s documents" % data_type)
        try:
            self.es.delete_by_query(
                index=self.index_name,
                body={"query": {"term": {"_doc_type": data_type}}},
                conflicts="proceed",
            )
        except NotFoundError:
            self.logger.warn("Index %s not found while dropping %s" % (self.index_name, data_type))
        self.logger.info("Dropped %s documents" % data_type)

    def add_obj(self, obj):
        self.add(obj.resource_content_type, Transforms.serialise(obj))

    @staticmethod
    def _make_doc_id(data_type, item_id):
        """Create a unique document ID by prefixing with the data_type.

        This prevents ID collisions between different model types that may
        share the same numeric primary key (e.g. a Bill with id=1 and a
        CommitteeMeeting with id=1).
        """
        return "%s_%s" % (data_type, item_id)

    def add_many(self, data_type, items):
        """Bulk index documents. Uses the ingest pipeline for types with attachments"""
        actions = []
        use_pipeline = any("attachment_data" in item for item in items)
        for item in items:
            doc_id = self._make_doc_id(data_type, item.pop("id"))
            item["_doc_type"] = data_type
            action = {"index": {"_index": self.index_name, "_id": doc_id}}
            actions.append(json.dumps(action))
            actions.append(json.dumps(item, default=str))

        body = "\n".join(actions) + "\n"

        kwargs = {"index": self.index_name, "body": body}
        if use_pipeline:
            kwargs["pipeline"] = ATTACHMENT_PIPELINE

        result = self.es.bulk(**kwargs)
        if result.get("errors"):
            for item in result["items"]:
                if "error" in item.get("index", {}):
                    self.logger.error(
                        "Bulk index error: %s", item["index"]["error"]
                    )

    def add(self, data_type, item):
        self.add_many(data_type, [item])

    def delete_obj(self, klass, id):
        self.delete(klass.resource_content_type, id)

    def delete(self, data_type, uid):
        try:
            self.es.delete(index=self.index_name, id=self._make_doc_id(data_type, uid))
        except NotFoundError:
            pass

    def get(self, data_type, uid):
        try:
            return self.es.get(index=self.index_name, id=self._make_doc_id(data_type, uid))
        except Exception:
            return False

    def indexable(self, obj):
        """ Should this object be indexed for searching? """
        return self.reindex_changes and obj.__class__ in Transforms.convert_rules

    def setup_attachment_pipeline(self):
        """Create or update the pipeline for processing attachment file data"""
        pipeline_body = {
            "description": "Extract text from attachment data",
            "processors": [
                {
                    "attachment": {
                        "field": "attachment_data",
                        "target_field": "attachment",
                        "indexed_chars": -1,
                        "ignore_missing": True,
                    }
                },
                {
                    "set": {
                        "field": "attachment_content_exact",
                        "value": "{{attachment.content}}",
                        "ignore_empty_value": True,
                    }
                },
                {
                    "remove": {
                        "field": "attachment_data",
                        "ignore_missing": True,
                    }
                },
            ],
        }
        self.es.ingest.put_pipeline(id=ATTACHMENT_PIPELINE, body=pipeline_body)
        self.logger.info("Ingest attachment pipeline created/updated.")

    def mapping(self):
        """Put the index mapping. In ES 7 there are no doc types,
        so we use a single mapping for all document types and
        distinguish them with a _doc_type field"""
        mapping = {
            "properties": {
                "_doc_type": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": True,
                    "fields": {
                        "exact": {
                            "type": "text",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "fulltext": {
                    "type": "text",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": True,
                    "fields": {
                        "exact": {
                            "type": "text",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "description": {
                    "type": "text",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": True,
                    "fields": {
                        "exact": {
                            "type": "text",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "number": {"type": "integer"},
                "year": {"type": "integer"},
                # attachment.content is populated by the ingest-attachment pipeline
                "attachment": {
                    "properties": {
                        "content": {
                            "type": "text",
                            "analyzer": "english",
                            "term_vector": "with_positions_offsets",
                            "store": True,
                        }
                    }
                },
                "attachment_content_exact": {
                    "type": "text",
                    "analyzer": "english_exact",
                    "store": True,
                    "term_vector": "with_positions_offsets",
                },
                "date": {"type": "date", "ignore_malformed": True},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "committee_id": {"type": "integer"},
                "committee_name": {"type": "keyword"},
                "minister_id": {"type": "integer"},
                "house_name": {"type": "keyword"},
                "house_name_short": {"type": "keyword"},
                "model_id": {"type": "integer"},
                "url": {"type": "keyword"},
                "api_url": {"type": "keyword"},
                "slug_prefix": {"type": "keyword"},
            }
        }
        self.es.indices.put_mapping(index=self.index_name, body=mapping)

    def build_filters(
        self,
        start_date,
        end_date,
        document_type,
        committee,
        updated_since,
        exclude_document_types,
    ):
        filters = []

        if start_date and end_date:
            filters.append({"range": {"date": {"gte": start_date, "lte": end_date}}})

        if committee:
            filters.append({"term": {"committee_id": committee}})

        if document_type:
            filters.append({"term": {"_doc_type": document_type}})

        if exclude_document_types:
            filters.append({
                "bool": {
                    "must_not": [
                        {"term": {"_doc_type": dt}} for dt in exclude_document_types
                    ]
                }
            })

        if updated_since:
            filters.append({"range": {"updated_at": {"gte": updated_since}}})

        return filters

    def _split_filters(self, filters, exclude_key=None):
        # tag filters by what they filter on
        tagged = []
        for f in filters:
            if "range" in f and "date" in f["range"]:
                tagged.append(("date", f))
            elif "term" in f and "_doc_type" in f["term"]:
                tagged.append(("document_type", f))
            elif "bool" in f and "must_not" in f["bool"]:
                tagged.append(("document_type_excludes", f))
            elif "term" in f and "committee_id" in f["term"]:
                tagged.append(("committee", f))
            elif "range" in f and "updated_at" in f["range"]:
                tagged.append(("updated_at", f))
            else:
                tagged.append((None, f))

        if exclude_key:
            return [f for tag, f in tagged if tag != exclude_key]
        return [f for _, f in tagged]

    def build_query(self, query):
        """ Build and return the query and highlight query portions of an ES call.
        This splits handles both phrases and simple terms.
        """

        phrases = [p[0].strip() for p in PHRASE_RE.findall(query)]
        phrases = [p for p in phrases if p]
        terms = PHRASE_RE.sub("", query).strip()

        if not terms and not phrases:
            raise ValueError("No search given")

        q = {"bool": {"must": []}}

        if phrases:
            # match to a phrase
            q["bool"]["must"].extend(
                {
                    "multi_match": {
                        "query": p,
                        "fields": self.exact_search_fields,
                        "type": "phrase",
                    },
                }
                for p in phrases
            )

        if terms:
            # We do two queries, one is a general term query across the fields,
            # the other is a phrase query. At the very least, items *must*
            # match the term search, and items are preferred if they
            # also match the phrase search.

            q["bool"]["must"].append(
                {
                    # best across all the fields
                    "multi_match": {
                        "query": terms,
                        "fields": self.search_fields,
                        "type": "best_fields",
                        "operator": "and",
                    }
                }
            )
            q["bool"]["should"] = {
                # try to match to a phrase
                "multi_match": {
                    "query": terms,
                    "fields": self.search_fields,
                    "type": "phrase",
                },
            }

        highlight_q = copy.deepcopy(q)
        highlight_q["bool"].pop("should", None)
        # boost phrase matches in highlight query
        for mm in [m["multi_match"] for m in highlight_q["bool"]["must"]]:
            if mm["type"] == "phrase":
                mm["boost"] = 5

        return q, highlight_q

    MAX_RESULT_WINDOW = 10000

    def search(
        self,
        query,
        size=10,
        es_from=0,
        start_date=False,
        end_date=False,
        document_type=False,
        committee=False,
        updated_since=None,
        exclude_document_types=None,
    ):
        # Cap from + size to stay within ES's max_result_window
        if es_from + size > self.MAX_RESULT_WINDOW:
            es_from = max(self.MAX_RESULT_WINDOW - size, 0)

        filters = self.build_filters(
            start_date,
            end_date,
            document_type,
            committee,
            updated_since,
            exclude_document_types,
        )

        q, highlight_q = self.build_query(query)

        q = {
            "function_score": {
                "query": q,
                "gauss": {
                    "date": {
                        # Scores must decay, starting at docs from 7 days ago
                        # such that docs 30 days ago are at 0.6.
                        # See https://www.elastic.co/blog/found-function-scoring
                        "offset": "7d",
                        "scale": "30d",
                        "decay": 0.6,
                    }
                },
            }
        }

        type_agg_filters = self._split_filters(filters, exclude_key="document_type")
        year_agg_filters = self._split_filters(filters, exclude_key="date")

        aggs = {
            "types": {
                "filter": {"bool": {"must": type_agg_filters}} if type_agg_filters else {"match_all": {}},
                "aggs": {"types": {"terms": {"field": "_doc_type", "size": 50}}},
            },
            "years": {
                "filter": {"bool": {"must": year_agg_filters}} if year_agg_filters else {"match_all": {}},
                "aggs": {
                    "years": {"date_histogram": {"field": "date", "calendar_interval": "year"}}
                },
            },
        }

        q = {
            "from": es_from,
            "size": size,
            "sort": {"_score": {"order": "desc"}},
            # don't return big fields
            "_source": {"excludes": ["fulltext", "description", "attachment", "attachment_data", "attachment_content_exact"]},
            "query": q,
            # filter the results after the query, so that the per-aggregation filters
            # aren't impacted by these filters. See
            # https://www.elastic.co/guide/en/elasticsearch/reference/7.17/filter-search-results.html#post-filter
            "post_filter": {"bool": {"must": filters}} if filters else {"match_all": {}},
            "aggs": aggs,
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "order": "score",
                "no_match_size": 0,
                "highlight_query": highlight_q,
                "fields": {
                    "title": {
                        "number_of_fragments": 0,
                        "matched_fields": ["title", "title.exact"],
                    },
                    "description": {
                        "number_of_fragments": 2,
                        "matched_fields": ["description", "description.exact"],
                        "type": "fvh",
                    },
                    "fulltext": {
                        "number_of_fragments": 2,
                        "matched_fields": ["fulltext", "fulltext.exact"],
                        "type": "fvh",
                    },
                    "attachment.content": {"number_of_fragments": 2},
                    "attachment_content_exact": {"number_of_fragments": 2},
                },
            },
        }

        self.logger.debug("query_statement: %s" % json.dumps(q, indent=2))
        return self.es.search(index=self.index_name, body=q)

    def reindex_everything(self):
        data_types = Transforms.data_types()

        self.logger.info("Reindexing everything: %s" % data_types)
        self.delete_everything()
        self.create_index()

        for data_type in data_types:
            self.reindex_all(data_type)

    def delete_everything(self):
        self.logger.info("Deleting index '%s'..." % self.index_name)
        try:
            self.es.indices.delete(index=self.index_name)
            self.logger.info("Index '%s' deleted." % self.index_name)
        except NotFoundError:
            self.logger.info("Index '%s' not found." % self.index_name)

    def create_index(self):
        self.logger.info("Creating index '%s'..." % self.index_name)
        settings = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "english_exact": {"tokenizer": "standard", "filter": ["lowercase"]}
                    }
                }
            }
        }
        try:
            self.es.indices.create(index=self.index_name, body=settings)
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                self.logger.info("Index '%s' already exists." % self.index_name)
            else:
                raise

        self.setup_attachment_pipeline()
        self.mapping()


class Transforms:
    """
    Each API model in PMG has different fields, so we need to describe how to map
    the model into something that can be indexed by Elasticsearch.

    Most models correspond directly to a single content type in ES. One or two
    of them are combined into one type so that we can support legacy and modern
    models (eg. QuestionReply and CommitteeQuestion).
    """

    @classmethod
    def data_types(cls):
        return sorted(
            list(set(k.resource_content_type for k in list(cls.convert_rules.keys())))
        )

    # If there is a rule defined here, the corresponding CamelCase model
    # will be indexed
    convert_rules = {
        Committee: {
            "title": "name",
            "description": "about",
            "house_name": "house.name",
            "house_name_short": "house.name_short",
        },
        CommitteeMeeting: {
            "title": "title",
            "description": "summary",
            "fulltext": "body",
            "date": "date",
            "committee_name": "committee.name",
            "committee_id": "committee.id",
            "house_name": "committee.house.name",
            "house_name_short": "committee.house.name_short",
        },
        CommitteeQuestion: {
            "id": ["slug_prefix", "id"],
            "title": "intro",
            "fulltext": ["question", "answer"],
            "date": "date",
            "committee_name": "minister.committee.name",
            "committee_id": "minister.committee.id",
            "minister_id": "minister.id",
        },
        Member: {
            "title": "name",
            "description": "bio",
            "house_name": "house.name",
            "house_name_short": "house.name_short",
        },
        Bill: {
            "title": "title",
            "year": "year",
            "number": "number",
            "code": "code",
            "attachment_data": "latest_version_for_indexing",
            "house_name": "place_of_introduction.name",
            "house_name_short": "place_of_introduction.name_short",
        },
        Hansard: {"title": "title", "fulltext": "body", "date": "date"},
        Briefing: {
            "title": "title",
            "description": "summary",
            "fulltext": "body",
            "date": "date",
            "committee_name": "committee.name",
            "committee_id": "committee.id",
        },
        QuestionReply: {
            "id": ["slug_prefix", "id"],
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": "minister.committee.name",
            "committee_id": "minister.committee.id",
            "minister_id": "minister.id",
        },
        TabledCommitteeReport: {
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": "committee.name",
            "committee_id": "committee.id",
            "house_name": "committee.house.name",
            "house_name_short": "committee.house.name_short",
        },
        CallForComment: {
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": "committee.name",
            "committee_id": "committee.id",
            "house_name": "committee.house.name",
            "house_name_short": "committee.house.name_short",
        },
        PolicyDocument: {"title": "title", "date": "start_date"},
        Gazette: {"title": "title", "date": "start_date"},
        DailySchedule: {"title": "title", "fulltext": "body", "date": "start_date"},
        Post: {"title": "title", "fulltext": "body", "date": "date", "slug": "slug"},
        Petition: {
            "title": "title",
            "description": "description",
            "attachment_data": "issue",
            "date": "date",
            "petitioner": "petitioner",
            "house_name": "house.name",
            "house_name_short": "house.name_short",
        },
    }

    @classmethod
    def serialise(cls, obj):
        item = {
            "model_id": obj.id,
            "url": obj.url,
            "api_url": obj.api_url,
            "slug_prefix": obj.slug_prefix,
            "created_at": obj.created_at.astimezone(pytz.utc).isoformat(),
            "updated_at": obj.updated_at.astimezone(pytz.utc).isoformat(),
        }

        rules = Transforms.convert_rules[obj.__class__]
        if "id" not in rules:
            item["id"] = obj.id

        for key, field in list(rules.items()):
            val = cls.get_val(obj, field)
            if isinstance(val, str):
                val = BeautifulSoup(val, "html.parser").get_text().strip()
            elif isinstance(val, (datetime.datetime, datetime.date)):
                # ES 7's strict_date_optional_time requires ISO 8601 with 'T' separator.
                # Python's str(datetime) uses a space separator which ES rejects.
                val = val.isoformat()
            item[key] = val

        return item

    @classmethod
    def get_val(cls, obj, field):
        if isinstance(field, list):
            # join multiple fields
            vals = (cls.get_val(obj, f) or "" for f in field)
            vals = [str(v) if not isinstance(v, str) else v for v in vals]
            return " ".join(vals)

        elif "." in field:
            # get nested attributes: foo.bar.baz
            for part in field.split("."):
                if not obj:
                    return None
                obj = getattr(obj, part)
            return obj

        else:
            # simple attribute name
            return getattr(obj, field)
