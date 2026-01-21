from builtins import str
from builtins import range

import math
import logging
import json
from collections import OrderedDict
import re
import copy
import pickle

from pyelasticsearch import ElasticSearch
from pyelasticsearch.exceptions import ElasticHttpNotFoundError
import pytz

from bs4 import BeautifulSoup

from . import db, app
from pmg.models.resources import *  # noqa
from pmg.models.posts import Post
from pmg.models.base import resource_slugs

PHRASE_RE = re.compile(r'"([^"]*)("|$)')
MAX_INDEXABLE_BYTES = 104857600  # Limit ElasticSearch/Netty has by default


class Search:

    esserver = app.config["ES_SERVER"]
    index_name = "pmg"
    search_fields = ["title^2", "description", "fulltext", "attachments"]
    exact_search_fields = [
        "title.exact^2",
        "description.exact",
        "fulltext.exact",
        "attachments_exact",
    ]
    es = ElasticSearch(esserver)
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

    def reindex_all(self, data_type):
        """ Index all content of a data_type """
        try:
            self.drop_index(data_type)
        except:
            self.logger.warn("Couldn't find %s index" % data_type)

        self.mapping(data_type)

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
        self.logger.info("Dropping %s index" % data_type)
        self.es.delete_all(self.index_name, data_type)
        self.logger.info("Dropped %s index" % data_type)

    def add_obj(self, obj):
        self.add(obj.resource_content_type, Transforms.serialise(obj))

    def add_many(self, data_type, items):
        self.es.bulk_index(self.index_name, data_type, items)

    def add(self, data_type, item):
        self.add_many(data_type, [item])

    def delete_obj(self, klass, id):
        self.delete(klass.resource_content_type, id)

    def delete(self, data_type, uid):
        try:
            self.es.delete(self.index_name, data_type, uid)
        except ElasticHttpNotFoundError:
            pass

    def get(self, data_type, uid):
        try:
            return self.es.get(self.index_name, data_type, uid)
        except:
            return False

    def indexable(self, obj):
        """ Should this object be indexed for searching? """
        return self.reindex_changes and obj.__class__ in Transforms.convert_rules

    def mapping(self, data_type):
        mapping = {
            "properties": {
                "title": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": "yes",
                    "fields": {
                        "exact": {
                            "type": "string",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "fulltext": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": "yes",
                    "fields": {
                        "exact": {
                            "type": "string",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "description": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets",
                    "term_vector": "with_positions_offsets",
                    "store": "yes",
                    "fields": {
                        "exact": {
                            "type": "string",
                            "analyzer": "english_exact",
                            "term_vector": "with_positions_offsets",
                        },
                    },
                },
                "number": {"type": "integer",},
                "year": {"type": "integer",},
                "attachments": {
                    "type": "attachment",
                    "fields": {
                        "attachments": {
                            "type": "string",
                            "analyzer": "english",
                            "term_vector": "with_positions_offsets",
                            "store": "yes",
                            "copy_to": "attachments_exact",
                        },
                    },
                },
                "attachments_exact": {
                    "type": "string",
                    "analyzer": "english_exact",
                    "store": "yes",
                    "term_vector": "with_positions_offsets",
                },
            }
        }
        self.es.put_mapping(self.index_name, data_type, mapping)

    def build_filters(
        self,
        start_date,
        end_date,
        document_type,
        committee,
        updated_since,
        exclude_document_types,
    ):
        filters = {}

        if start_date and end_date:
            filters["date"] = {"range": {"date": {"gte": start_date, "lte": end_date,}}}

        if committee:
            filters["committe"] = {"term": {"committee_id": committee}}

        if document_type:
            filters["document_type"] = {
                "term": {"_type": document_type},
            }

        if exclude_document_types:
            filters["document_type_excludes"] = {
                "not": {
                    "or": [{"term": {"_type": dt}} for dt in exclude_document_types],
                }
            }

        if updated_since:
            filters["updated_at"] = {"range": {"updated_at": {"gte": updated_since,}}}

        return filters

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
                        # this helps skip stopwords, see
                        # http://www.elasticsearch.org/blog/stop-stopping-stop-words-a-look-at-common-terms-query/
                        "cutoff_frequency": 0.0007,
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

        aggs = {
            "types": {
                "filter": {
                    "and": {
                        "filters": [
                            v for k, v in list(filters.items()) if k != "document_type"
                        ]
                    }
                },
                "aggs": {"types": {"terms": {"field": "_type"}}},
            },
            "years": {
                "filter": {
                    "and": {
                        "filters": [v for k, v in list(filters.items()) if k != "date"]
                    }
                },
                "aggs": {
                    "years": {"date_histogram": {"field": "date", "interval": "year"},}
                },
            },
        }

        q = {
            "from": es_from,
            "size": size,
            "sort": {"_score": {"order": "desc"}},
            # don't return big fields
            "_source": {"exclude": ["fulltext", "description", "attachments"]},
            "query": q,
            # filter the results after the query, so that the per-aggregation filters
            # aren't impacted by these filters. See
            # http://www.elasticsearch.org/guide/en/elasticsearch/guide/current/_post_filter.html
            "post_filter": {"and": {"filters": list(filters.values())}},
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
                    "attachments": {"number_of_fragments": 2,},
                    "attachments_exact": {"number_of_fragments": 2,},
                },
            },
        }

        self.logger.debug("query_statement: %s" % json.dumps(q, indent=2))
        return self.es.search(q, index=self.index_name)

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
            self.es.delete_index(self.index_name)
            self.logger.info("Index '%s' deleted." % self.index_name)
        except ElasticHttpNotFoundError:
            self.logger.info("Index '%s' not found." % self.index_name)

    def create_index(self):
        self.logger.info("Creating index '%s'..." % self.index_name)
        settings = {
            "analysis": {
                "analyzer": {
                    "english_exact": {"tokenizer": "standard", "filter": ["lowercase"]}
                }
            }
        }
        self.es.create_index(self.index_name, settings=settings)


class Transforms:
    """
    Each API model in PMG has different fields, so we need to describe how to map
    the model into something that can be indexed by ElasticSearch.

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
        #CommitteeQuestion: {
        #    "id": ["slug_prefix", "id"],
        #    "title": "intro",
        #    "fulltext": ["question", "answer"],
        #    "date": "date",
        #    "committee_name": "minister.committee.name",
        #    "committee_id": "minister.committee.id",
        #    "minister_id": "minister.id",
        #},
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
            "attachments": "latest_version_for_indexing",
            "house_name": "place_of_introduction.name",
            "house_name_short": "place_of_introduction.name_short",
        },
        Hansard: {"title": "title", "fulltext": "body", "date": "date",},
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
        PolicyDocument: {"title": "title", "date": "start_date",},
        Gazette: {"title": "title", "date": "start_date",},
        DailySchedule: {"title": "title", "fulltext": "body", "date": "start_date",},
        Post: {"title": "title", "fulltext": "body", "date": "date", "slug": "slug",},
        Petition: {
            "title": "title",
            "description": "description",
            "attachments": "issue",
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
