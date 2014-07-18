import sqlalchemy
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from database import engine

Base = declarative_base()


def __content_type_repr__(self):
    return "<Content_type(pk='%s')>" % self.pk


def get_content_type_model(model_name, fields, model=Base):
    """
    Meta-class for generating database model classes.
    Creates models on the fly, using the builtin 'type' metaclass, see
    http://stackoverflow.com/questions/100003/what-is-a-metaclass-in-python
    """

    field_defs = {
        '__tablename__': model_name.lower(),
        '__repr__': __content_type_repr__,
        'pk': Column(Integer, primary_key=True),
        }

    for field in fields:
        field_defs[field] = Column(String)

    tmp = type(model_name, (model,), field_defs)

    # create the database table if necessary
    Base.metadata.create_all(engine)
    return tmp


if __name__ == "__main__":

    model_name = 'bill'
    fields = [u'files', u'audio', u'terms', u'vid', u'title', u'file_bill_fid', u'file_bill_list', u'nid', u'bill_tracker_link_attributes', u'file_bill_description', u'version', u'bill_tracker_link_title', u'content_type', u'delta', u'effective_date', u'file_bill_data', u'_id', u'start_date', u'bill_tracker_link_url', u'revisions']

    model = get_content_type_model(model_name, fields)
