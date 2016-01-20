from flask import abort
from flask.ext.admin import expose, BaseView

from .rbac import RBACMixin
from pmg import db


class Report(object):
    def __init__(self, id, name, description, sql):
        self.id = id
        self.name = name
        self.description = description
        self.sql = sql

    def run(self):
        return db.engine.execute(self.sql)


class ReportView(RBACMixin, BaseView):
    required_roles = ['editor', ]

    REPORTS = (
        Report(1,
               name="Files linked to committees",
               description="Uploaded files linked to committees by month",
               sql="""
select
  to_char(e.date, 'YYYY-MM') as "date",
  count(distinct ef.file_id) as "newly uploaded files associated with a committee"
from
  event e
  inner join event_files ef on ef.event_id = e.id
where
  e.type = 'committee-meeting'
group by
  to_char(e.date, 'YYYY-MM')
order by
  to_char(e.date, 'YYYY-MM') desc
"""),
    )

    @expose('/')
    def index(self):
        return self.render('admin/reports/index.html', reports=self.REPORTS)

    @expose('/<int:id>')
    def report(self, id):
        reports = [r for r in self.REPORTS if r.id == id]
        if not reports:
            return abort(404)
        report = reports[0]
        result = report.run()
        return self.render('admin/reports/report.html', report=report, result=result)
