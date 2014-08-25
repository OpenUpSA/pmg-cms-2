import json
from datetime import datetime, date
from backend import db, logger
from backend import app
from operator import itemgetter

API_HOST = app.config["API_HOST"]


class CustomEncoder(json.JSONEncoder):
    """
    Define encoding rules for fields that are not readily serializable.
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            encoded_obj = obj.strftime("%B %d, %Y, %H:%M")
        elif isinstance(obj, date):
            encoded_obj = obj.strftime("%B %d, %Y")
        elif isinstance(obj, db.Model):
            try:
                encoded_obj = json.dumps(obj.to_dict(), cls=CustomEncoder, indent=4)
            except Exception:
                encoded_obj = str(obj)
        else:
            encoded_obj = json.JSONEncoder.default(self, obj)
        return encoded_obj


def model_to_dict(obj):
    """
    Convert a single model object, or a list of model objects to dicts.
    Handle nested resources recursively.
    """

    # attributes from columns
    columns = obj.__mapper__.column_attrs.keys()
    tmp_dict = {
        key: getattr(obj, key) for key in columns
    }
    # attributes from relations are ignored
    return tmp_dict


def queryset_to_json(obj_or_list, count=None, next=None):
    """
    Convert a single model object, or a list of model objects to dicts, before
    serializing the results as a json string.
    """

    if isinstance(obj_or_list, db.Model):
        logger.debug("single obj")
        # this a single object
        out = model_to_dict(obj_or_list)
    else:
        # this is a list of objects
        logger.debug("list of objs")
        results = []
        for obj in obj_or_list:
            results.append(model_to_dict(obj))
        out = {
            'count': count,
            'next': next,
            'results': results
            }

    return json.dumps(out, cls=CustomEncoder, indent=4)