from sqlalchemy.sql.expression import and_, or_


# Monkey patch the flask admin ajax lookup to be case sensitive
# see https://github.com/mrjoes/flask-admin/pull/789
from flask.ext.admin.contrib.sqla.ajax import QueryAjaxModelLoader, DEFAULT_PAGE_SIZE
def get_list_case_insensitive(self, term, offset=0, limit=DEFAULT_PAGE_SIZE):
    query = self.session.query(self.model)

    filters = (field.ilike(u'%%%s%%' % term) for field in self._cached_fields)
    query = query.filter(or_(*filters))

    return query.offset(offset).limit(limit).all()
QueryAjaxModelLoader.get_list = get_list_case_insensitive
