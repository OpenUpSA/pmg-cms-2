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
        Report(2,
               name="Bill events",
               description="Events dates for bills",
               sql="""
select
  b.id,
  b.year,
  b.number,
  bt.name,
  b.title,
  bs.description as "status",
  to_char(b.date_of_introduction, 'YYYY-MM-DD') as "date_of_introduction",
  (select to_char(e.date, 'YYYY-MM-DD') as "event_date"
   from event e
   inner join event_bills eb on e.id = eb.event_id and eb.bill_id = b.id
   where e.type in ('bill-passed', 'bill-updated')
   order by e.date desc
   limit 1) as "date_of_adoption",
  to_char(b.date_of_assent, 'YYYY-MM-DD') as "date_of_assent",
  (select to_char(e.date, 'YYYY-MM-DD') as "event_date"
   from event e
   inner join event_bills eb on e.id = eb.event_id and eb.bill_id = b.id
   where e.type = 'bill-enacted'
   limit 1) as "date_of_enactment",
  (select to_char(e.date, 'YYYY-MM-DD') as "event_date"
   from event e
   inner join event_bills eb on e.id = eb.event_id and eb.bill_id = b.id
   where e.type = 'bill-act-commenced'
   limit 1) as "date_of_commencement"
from
  bill b
  inner join bill_type bt on b.type_id = bt.id
  inner join bill_status bs on bs.id = b.status_id
order by b.year desc nulls last, number asc nulls last
"""),
        Report(3,
               name="Committee meeting summary",
               description="Committee meeting dates, times and durations",
               sql="""
select
  to_char(e.date, 'YYYY-MM') as "date",
  to_char(e.date, 'YYYY') as "year",
  to_char(e.date, 'MM') as "month",
  h.name_short as "house",
  c.name as "committee",
  to_char(date '2011-01-01' + e.actual_start_time, 'HH12:MI') as "actual_start_time",
  to_char(date '2011-01-01' + e.actual_end_time, 'HH12:MI') as "actual_end_time",
  case when e.actual_start_time is not null and e.actual_end_time is not null
  then extract(epoch from ((date '2011-01-01' + e.actual_end_time) - (date '2011-01-01' + e.actual_start_time)))/60
  else null end as "minutes",
  e.title,
  e.id as "meeting-id",
  concat('https://pmg.org.za/committee-meeting/', e.id, '/') as "url"
from
  event e
  inner join committee c on c.id = e.committee_id
  inner join house h on h.id = c.house_id
where e.type = 'committee-meeting'
order by e.date desc
"""),
        Report(4,
               name="Minister questions summary",
               description="Questions to ministers",
               sql="""
select
  to_char(q.date, 'YYYY-MM') as "date",
  to_char(q.date, 'YYYY') as "year",
  to_char(q.date, 'MM') as "month",
  m.name as "minister",
  coalesce(mem.name, q.asked_by_name) as "asked by",
  p.name as "asked by party",
  q.id as "question-id",
  concat('https://pmg.org.za/committee-question/', q.id, '/') as "url"
from
  committee_question q
  inner join minister m on m.id = q.minister_id
  left outer join member mem on mem.id = q.asked_by_member_id
  left outer join party p on p.id = mem.party_id
order by q.date desc
"""),
        Report(5,
               name="Committee meeting attendance",
               description="Meeting attendance by Member",
               sql='''
select
  to_char(e.date, 'YYYY-MM-DD') as "date",
  to_char(e.date, 'YYYY') as "year",
  to_char(e.date, 'MM') as "month",
  c.name as "committee",
  a.meeting_id as "committee-meeting-id",
  m.name as "member",
  a.attendance as "attendance"
from
  event e
  inner join committee c on e.committee_id = c.id
  inner join committee_meeting_attendance a on a.meeting_id = e.id
  inner join member m on m.id = a.member_id
order by
  e.date desc,
  c.name,
  m.name'''),
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
        truncated = result.rowcount > 500
        rows = list(result)
        if truncated:
            rows = rows[0:500]

        return self.render(
            'admin/reports/report.html',
            report=report,
            result=result,
            rows=rows,
            truncated=truncated)
