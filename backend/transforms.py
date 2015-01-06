from bs4 import BeautifulSoup

class Transforms:
    @classmethod
    def data_types(cls):
        return cls.convert_rules.keys()

    # If there is a rule defined here, the corresponding CamelCase model
    # will be indexed
    convert_rules = {
        "committee": {
            "id": "id",
            "title": "name",
            "description": ["info", "about"]
        },
        "committee_meeting": {
            "id": "id",
            "title": "title",
            "description": "summary",
            "fulltext": "body",
            "date": "date",
            "committee_name": ["organisation", "name"],
            "committee_id": ["organisation", "id"],
        },
        "member": {
            "id": "id",
            "title": "name",
            "description": "bio",
            "date": "start_date",
        },
        "bill": {
            "id": "id",
            "title": "title",
            "description": "bill_code"
        },
        "hansard": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
        },
        "briefing": {
            "id": "id",
            "title": "title",
            "description": "summary",
            "fulltext": "minutes",
            "date": "start_date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "question_reply": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", 0, "name"],
            "committee_id": ["committee", 0, "id"],
        },
        "tabled_committee_report": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", 0, "name"],
            "committee_id": ["committee", 0, "id"],
        },
        "call_for_comment": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", 0, "name"],
            "committee_id": ["committee", 0, "id"],
        },
        "policy_document": {
            "id": "id",
            "title": "title",
            "date": "start_date",
        },
        "gazette": {
            "id": "id",
            "title": "title",
            "date": "start_date",
        },
        "daily_schedule": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
        },
    }

    @classmethod
    def serialise(cls, data_type, obj):
        item = {}
        for key, field in Transforms.convert_rules[data_type].iteritems():
            val = cls.get_val(obj, field)
            if isinstance(val, unicode):
                val = BeautifulSoup(val).get_text().strip()
            item[key] = val
        return item

    @classmethod
    def get_val(cls, obj, field):
        if isinstance(field, list):
            if (len(field) == 1):
                if hasattr(obj, field[0]):
                    return getattr(obj, field[0])
            key = field[:1][0]
            if isinstance(key, int):
                if len(obj) > key:
                    return cls.get_val(obj[key], field[1:])
                return None
            if hasattr(obj, key):
                newobj = getattr(obj, key)
                return cls.get_val(newobj, field[1:])
            else:
                return None
        else:
            return getattr(obj, field)

