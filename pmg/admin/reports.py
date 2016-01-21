from flask import abort, request, make_response
from flask.ext.admin import expose, BaseView

from .rbac import RBACMixin
from .xlsx import XLSXBuilder
from pmg import db


class Report(object):
    def __init__(self, id, name, description, sql):
        self.id = id
        self.name = name
        self.description = description
        self.sql = sql

    def run(self):
        return db.engine.execute(self.sql)

    def as_xlsx(self):
        result = self.run()
        xlsx = XLSXBuilder().from_resultset(result)

        resp = make_response(xlsx)
        resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        resp.headers['Content-Disposition'] = "attachment;filename=%s.xlsx" % self.filename()
        return resp

    def filename(self):
        return self.name.replace(r'[^A-Za-z0-9]', '')


class ReportView(RBACMixin, BaseView):
    required_roles = ['editor', ]

    REPORTS = (
        Report(1,
               name="Files linked to committees",
               description="Number of uploaded files linked to committees, by month",
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

        if request.args.get('format') == 'xlsx':
            return report.as_xlsx()

        result = report.run()
        return self.render('admin/reports/report.html', report=report, result=result)
