import logging
import os
from operator import itemgetter
import datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta

from flask import Flask, flash, redirect, url_for, request, render_template, g, abort, make_response
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.form import InlineModelConverter
from flask.ext.admin.contrib.sqla.fields import InlineModelFormList
from flask.ext.admin.contrib.sqla.filters import BaseSQLAFilter, DateBetweenFilter
from flask.ext.admin.model.form import InlineFormAdmin
from flask.ext.admin.model.template import macro
from flask.ext.security import current_user
from wtforms import fields
from wtforms.validators import required, optional
from sqlalchemy import func
from sqlalchemy.sql.expression import and_, or_
from werkzeug import secure_filename
from xlsx import XLSXBuilder

from pmg import app, db
from pmg.models import *

from .email_alerts import EmailAlertView
from .rbac import RBACMixin
import widgets

logger = logging.getLogger(__name__)


class MyIndexView(RBACMixin, AdminIndexView):
    required_roles = ['editor']

    @expose("/")
    def index(self):

        record_counts = [
            ('Members', 'member.index_view', Member.query.count()),
            ('Bill', 'bill.index_view', Bill.query.count()),
            ('Committee', 'committee.index_view', Committee.query.count()),
            ('Committee Meetings', 'committee-meeting.index_view', Event.query.filter_by(type="committee-meeting").count()),
            ('Questions & Replies', 'question.index_view', QuestionReply.query.count()),
            ('Calls for Comment', 'call-for-comment.index_view', CallForComment.query.count()),
            ('Daily Schedules', 'schedule.index_view', DailySchedule.query.count()),
            ('Gazette', 'gazette.index_view', Gazette.query.count()),
            ('Hansards', 'hansard.index_view', Event.query.filter_by(type="plenary").count()),
            ('Media Briefings', 'briefing.index_view', Event.query.filter_by(type="media-briefing").count()),
            ('Policy Documents', 'policy.index_view', PolicyDocument.query.count()),
            ('Tabled Committee Reports', 'tabled-committee-report.index_view', TabledCommitteeReport.query.count()),
            ('Uploaded Files', 'files.index_view', File.query.count()),
            ]
        record_counts = sorted(record_counts, key=itemgetter(2), reverse=True)

        return self.render(
            'admin/my_index.html',
            record_counts=record_counts)


class UsageReportView(RBACMixin, BaseView):
    required_roles = ['editor', ]

    def get_list(self, months):

        cutoff = datetime.datetime.utcnow()-relativedelta(months=months)
        organisation_list = db.session.query(
            Organisation.name,
            Organisation.domain,
            db.func.count(User.id).label("num_users")
        ).join(
            Organisation.users
        ).filter(
            User.current_login_at > cutoff
        ).group_by(
            Organisation.id
        ).order_by(
            Organisation.name
        ).all()
        return organisation_list

    @expose('/')
    @expose('/<int:months>/')
    def index(self, months=1):

        return self.render('admin/usage_report.html', org_list=self.get_list(months), num_months=months, today=datetime.date.today())

    def xlsx(self, users, filename):
        out = XLSXBuilder(users)
        xlsx = out.build()
        resp = make_response(xlsx)
        resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        resp.headers['Content-Disposition'] = "attachment;filename=" + filename
        return resp

    @expose('/xlsx/<int:months>/')
    def download(self, months=1):

        today=datetime.date.today()
        tmp = str(months) + " month up to " + str(today)
        if months > 1:
            tmp = str(months) + " months up to " + str(today)
        filename = "PMG active organisations - " + tmp + ".xlsx"
        return self.xlsx(self.get_list(months), filename=filename)


class MyModelView(RBACMixin, ModelView):
    required_roles = ['editor']

    can_create = True
    can_edit = True
    can_delete = True
    edit_template = 'admin/my_edit.html'
    create_template = 'admin/my_create.html'
    list_template = 'admin/my_list.html'

    def __init__(self, *args, **kwargs):
        if 'frontend_url_format' in kwargs:
            self.frontend_url_format = kwargs.pop('frontend_url_format')

        super(MyModelView, self).__init__(*args, **kwargs)

    def frontend_url(self, model):
        if getattr(self, 'frontend_url_format', None):
            return '/' + self.frontend_url_format % self.get_pk_value(model)
        return None


class HasExpiredFilter(BaseSQLAFilter):
    def __init__(self, column, name):
        options = (
                ('expired', 'Expired'),
                ('unexpired', 'Not expired'),
                ('1month', 'Expiring in 1 month'),
                ('3month', 'Expiring in 3 months'),
                ('6month', 'Expiring in 6 months'),
                ('1year', 'Expiring in 1 year'),
            )
        super(HasExpiredFilter, self).__init__(column, name, options=options)

    def apply(self, query, value):
        if value == 'expired':
            return query\
                    .filter(self.column != None)\
                    .filter(self.column < datetime.date.today())

        elif value == 'unexpired':
            return query.filter(or_(
                        self.column == None,
                        self.column >= datetime.date.today()))

        elif value == '1month':
            return query\
                    .filter(self.column >= datetime.date.today())\
                    .filter(self.column <= datetime.date.today() + relativedelta(months=1))

        elif value == '3month':
            return query\
                    .filter(self.column >= datetime.date.today())\
                    .filter(self.column <= datetime.date.today() + relativedelta(months=3))

        elif value == '6month':
            return query\
                    .filter(self.column >= datetime.date.today())\
                    .filter(self.column <= datetime.date.today() + relativedelta(months=6))

        elif value == '1year':
            return query\
                    .filter(self.column >= datetime.date.today())\
                    .filter(self.column <= datetime.date.today() + relativedelta(years=1))

        else:
            return query

    def operation(self):
        return 'is'


class UserView(MyModelView):
    required_roles = ['user-admin']

    can_create = True
    can_delete = True
    column_list = [
        'email',
        'active',
        'confirmed_at',
        'current_login_at',
        'login_count',
        'expiry',
        ]
    column_labels = {
        'current_login_at': "Last seen",
        'subscriptions': "User's premium subscriptions",
        }
    form_columns = [
        'email',
        'name',
        'active',
        'roles',
        'organisation',
        'expiry',
        'subscribe_daily_schedule',
        'subscriptions',
        'committee_alerts',
        ]
    form_args = {
        'subscriptions': {
            'query_factory': Committee.premium_for_select,
            'widget': widgets.CheckboxSelectWidget(multiple=True),
            }
        }
    column_formatters = {'current_login_at': macro("datetime_as_date")}
    column_searchable_list = ('email',)
    column_filters = [
            HasExpiredFilter(User.expiry, 'Subscription expiry'),
            DateBetweenFilter(User.expiry, 'Expiry date'),
            ]


class OrganisationView(MyModelView):
    can_create = True

    column_list = [
        'name',
        'domain',
        'paid_subscriber',
        'expiry',
        ]
    column_searchable_list = ('domain', 'name')
    column_filters = [
            HasExpiredFilter(Organisation.expiry, 'Subscription expiry'),
            DateBetweenFilter(Organisation.expiry, 'Expiry date'),
            ]
    form_ajax_refs = {
        'users': {
            'fields': ('name', 'email'),
            'page_size': 25
        },
    }
    form_excluded_columns = [
        'created_at',
        ]
    form_args = {
        'subscriptions': {
            'query_factory': Committee.premium_for_select,
            'widget': widgets.CheckboxSelectWidget(multiple=True)
            }
        }
    column_labels = {'subscriptions': "Premium subscriptions"}


class CommitteeView(MyModelView):
    frontend_url_format = 'committee/%s'
    can_delete = False

    column_list = (
        'name',
        'house',
        'ad_hoc',
        'memberships'
    )
    column_labels = {'memberships': 'Members', }
    column_sortable_list = (
        'name',
        ('house', 'house.name'),
        'ad_hoc',
    )
    column_default_sort = (Committee.name, False)
    column_searchable_list = ('name', )
    column_formatters = dict(
        memberships=macro('render_membership_count'),
        )
    form_columns = (
        'name',
        'ad_hoc',
        'premium',
        'house',
        'memberships',
    )
    form_args = {
        'memberships': {'widget': widgets.InlineMembershipsWidget()},
    }
    inline_models = (Membership, )


class ViewWithFiles(object):
    """ Mixin to pre-fill inline file forms. """

    form_args = {
        'files': {'widget': widgets.InlineFileWidget()},
    }

    def on_form_prefill(self, form, id):
        if hasattr(form, 'files'):
            for f in form.files:
                f.title.data = f.object_data.file.title


class InlineFile(InlineFormAdmin):
    """ Inline file admin for all views that allow file attachments.
    It allows the user to choose an existing file to link as
    an attachment, or upload a new one. It also allows the user
    to edit the title of an already-attached file.
    """
    form_columns = (
        'id',
        'file',
        )
    column_labels = {'file': 'Existing file', }
    form_ajax_refs = {
        'file': {
            'fields': ('title', 'file_path'),
            'page_size': 10,
        }
    }

    def postprocess_form(self, form_class):
        # add a field for handling the file upload
        form_class.upload = fields.FileField('Upload a file')
        form_class.file.kwargs['validators'] = []
        form_class.file.kwargs['allow_blank'] = True
        form_class.title = fields.TextField('Title')
        return form_class

    def on_model_change(self, form, model):
        # save file, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            # always create a new file, don't overwrite
            model.file = File()
            model.file.from_upload(file_data)
        if form.title.data:
            model.file.title = form.title.data


class EventView(ViewWithFiles, MyModelView):

    form_excluded_columns = ('type', )
    column_exclude_list = ('type', )

    def __init__(self, model, session, **kwargs):
        self.type = kwargs.pop('type')
        super(EventView, self).__init__(model, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            # set some default values when creating a new record
            model.type = self.type
        # make sure the new date is timezone aware
        if model.date:
            model.date = model.date.replace(tzinfo=tz.tzlocal())

    def get_query(self):
        """
        Add filter to return only records of the specified type.
        """

        return self.session.query(self.model) \
            .filter(self.model.type == self.type)

    def get_count_query(self):
        """
        Add filter to return only records of the specified type.
        """

        return self.session.query(func.count('*')).select_from(self.model) \
            .filter(self.model.type == self.type)


class CommitteeMeetingView(EventView):
    frontend_url_format = 'committee-meeting/%s'

    column_list = ('date', 'title', 'committee', 'featured')
    column_labels = {'committee': 'Committee', }
    column_sortable_list = (
        'date',
        ('committee', 'committee.name'),
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('committee.name', 'title')
    form_columns = (
        'committee',
        'title',
        'date',
        'chairperson',
        'featured',
        'public_participation',
        'bills',
        'summary',
        'body',
        'files',
    )
    form_args = {
        'committee': {'validators': [required()]},
        'files': {'widget': widgets.InlineFileWidget()},
    }
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        'summary': {'class': 'custom-ckeditor'}
    }
    form_ajax_refs = {
        'bills': {
            'fields': ('title',),
            'page_size': 50
        }
    }
    inline_models = [InlineFile(EventFile)]


class HansardView(EventView):
    frontend_url_format = 'hansard/%s'

    column_list = (
        'title',
        'date',
    )
    column_sortable_list = (
        'title',
        'date',
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', )
    form_columns = (
        'date',
        'title',
        'body',
        'files',
    )
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        }
    inline_models = [InlineFile(EventFile)]

class BriefingView(EventView):
    frontend_url_format = 'briefing/%s'

    column_list = (
        'title',
        'date',
        'committee',
    )
    column_sortable_list = (
        'title',
        'date',
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', )
    form_columns = (
        'title',
        'date',
        'committee',
        'summary',
        'body',
        'files',
    )
    form_widget_args = {
        'summary': {'class': 'custom-ckeditor'},
        'body': {'class': 'custom-ckeditor'},
        }
    inline_models = [InlineFile(EventFile)]


class MemberView(MyModelView):
    frontend_url_format = 'member/%s'

    column_list = (
        'name',
        'house',
        'party',
        'province',
        'memberships',
        'current',
        'pa_link',
        'profile_pic_url',
    )
    column_labels = {
        'memberships': 'Committees',
        'current': 'Currently active',
        'pa_link': 'PA Link',
        }
    column_sortable_list = (
        'name',
        ('house', 'house.name'),
        ('party', 'party.name'),
        ('province', 'province.name'),
        'bio',
        'profile_pic_url',
    )
    column_default_sort = (Member.name, False)
    column_searchable_list = ('name', )
    column_formatters = dict(
        profile_pic_url=macro('render_profile_pic'),
        memberships=macro('render_committee_membership'),
        pa_link=macro('render_external_link'),
        )
    column_filters = ['current', 'house.name', 'party.name', 'province.name']
    form_columns = (
        'name',
        'current',
        'house',
        'party',
        'province',
        'bio',
        'pa_link',
        'upload',
    )
    form_extra_fields = {
        'upload': fields.FileField('Profile pic')
    }
    form_overrides = dict(bio=fields.TextAreaField)
    form_ajax_refs = {
        'events': {
            'fields': ('date', 'title', 'type'),
            'page_size': 25
        }
    }
    form_widget_args = {
        'bio': {
            'rows': '10'
        },
        }
    edit_template = "admin/edit_member.html"

    def on_model_change(self, form, model, is_created):
        # save profile pic, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            tmp = File()
            tmp.from_upload(file_data)
            model.profile_pic_url = tmp.file_path


class QuestionReplyView(MyModelView):
    frontend_url_format = 'question_reply/%s'

    column_list = (
        'committee',
        'title',
        'start_date',
        'question_number',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', 'question_number')
    form_columns = (
        'committee',
        'title',
        'start_date',
        'question_number',
        'body',
    )
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        }


class CallForCommentView(MyModelView):
    frontend_url_format = 'call-for-comment/%s'

    column_list = (
        'committee',
        'title',
        'start_date',
        'end_date',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_columns = (
        'committee',
        'title',
        'start_date',
        'end_date',
        'body',
    )
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        }


class DailyScheduleView(ViewWithFiles, MyModelView):
    frontend_url_format = 'daily_schedule/%s'

    column_exclude_list = (
        'body',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {
            'class': 'custom-ckeditor'
        },
    }
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(DailyScheduleFile)]


class GazetteView(ViewWithFiles, MyModelView):
    frontend_url_format = 'gazette/%s'

    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(GazetteFile)]


class PolicyDocumentView(ViewWithFiles, MyModelView):
    frontend_url_format = 'policy-document/%s'

    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(PolicyDocumentFile)]


class TabledCommitteeReportView(ViewWithFiles, MyModelView):
    frontend_url_format = 'tabled-committee-report/%s'

    column_exclude_list = (
        'body',
        'summary',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        'summary': {'class': 'custom-ckeditor'},
        }
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(TabledCommitteeReportFile)]


class EmailTemplateView(MyModelView):
    column_list = (
        'name',
        'subject',
        'description',
    )
    column_default_sort = ('name', True)
    column_searchable_list = ('name', 'subject', 'description', 'body')
    form_columns = (
        'name',
        'description',
        'subject',
        'body',
    )
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        }


class InlineBillEventsForm(InlineFormAdmin):
    form_columns = (
        'id',
        'date',
        'type',
        'title',
        'house',
        'member',
        )
    form_choices = {
        'type': [
            ('bill-introduced', 'Bill introduced'),
            ('bill-updated', 'Bill updated'),
            ('bill-passed', 'Bill passed'),
            ('bill-signed', 'Bill signed'),
            ('bill-enacted', 'Bill enacted'),
            ('bill-act-commenced', 'Act commenced'),
        ]
    }
    form_ajax_refs = {
        'member': {
            'fields': ('name',),
            'page_size': 25
        },
    }

    def on_model_change(self, form, model):
        # make sure the new date is timezone aware
        model.date = model.date.replace(tzinfo=tz.tzlocal())


class InlineBillVersionForm(InlineFormAdmin):
    form_columns = (
        'id',
        'date',
        'title',
        'file',
        )
    form_ajax_refs = {
        'file': {
            'fields': ('title',),
            'page_size': 25
            }
        }

    def postprocess_form(self, form_class):
        # TODO: hide this for existing versions
        form_class.upload = fields.FileField('Upload a new file')
        return form_class

    def on_model_change(self, form, model):
        # save file, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            if not model.file:
                model.file = File()

            model.file.from_upload(file_data)


class BillsView(MyModelView):
    column_list = (
        'code',
        'title',
        'type.name',
        'status.name',
    )
    column_labels = {
        'type.name': 'Type',
        'status.name': 'Status',
    }
    form_columns = (
        'year',
        'number',
        'title',
        'type',
        'introduced_by',
        'date_of_introduction',
        'place_of_introduction',
        'status',
        'date_of_assent',
        'effective_date',
        'act_name',
        'versions',
    )
    column_default_sort = ('year', True)
    column_searchable_list = ('title',)
    inline_models = [
        InlineBillEventsForm(Event),
        InlineBillVersionForm(BillVersion),
        ]
    form_args = {
        'events': {'widget': widgets.InlineBillEventsWidget()},
    }

class FeaturedContentView(MyModelView):
    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        model.start_date = model.start_date.replace(tzinfo=tz.tzlocal())


class FileView(MyModelView):
    can_create = False

    column_list = ('title', 'file_path')
    column_searchable_list = ('title', 'file_path')
    column_default_sort = 'file_path'
    form_columns = (
        'title',
        'description',
        'file_path',
        'file_mime',
    )
    form_widget_args = {
        'file_path': {'disabled': True},
        'file_mime': {'disabled': True}
    }


class RedirectView(MyModelView):
    column_list = ('old_url', 'new_url', 'nid')
    column_searchable_list = ('old_url', 'new_url')
    column_default_sort = 'old_url'

class PageView(MyModelView):
    column_list = ('slug', 'title')
    column_searchable_list = ('slug', 'title')
    column_default_sort = 'slug'

    form_columns = ('title', 'slug', 'path', 'body')
    form_extra_fields = {
        'path': fields.TextField('Path'),
    }
    form_widget_args = {
        'body': {'class': 'custom-ckeditor'},
        'path': {'readonly': True},
        }

    def frontend_url(self, model):
        return '/page/%s' % model.slug

    def on_form_prefill(self, form, id):
        form.path.data = '/page/%s' % form.slug.data


# initialise admin instance
admin = Admin(app, name='PMG-CMS', base_template='admin/my_base.html', index_view=MyIndexView(name='Home'), template_mode='bootstrap3')

# ---------------------------------------------------------------------------------
# Users
admin.add_view(UsageReportView(name="Usage report", endpoint='usage_report', category='Users'))
admin.add_view(UserView(User, db.session, name="Users", endpoint='user', category='Users'))
admin.add_view(OrganisationView(Organisation, db.session, name="Organisations", endpoint='organisation', category='Users'))

# ---------------------------------------------------------------------------------
# Committees
admin.add_view(CommitteeView(Committee, db.session, name="Committees", endpoint='committee', category="Committees"))
admin.add_view(CommitteeMeetingView(CommitteeMeeting, db.session, type="committee-meeting", name="Committee Meetings", endpoint='committee-meeting', category="Committees"))
admin.add_view(TabledCommitteeReportView(TabledCommitteeReport, db.session, name="Tabled Committee Reports", endpoint='tabled-committee-report', category="Committees"))

# ---------------------------------------------------------------------------------
# Members
admin.add_view(MemberView(Member, db.session, name="Members", endpoint='member'))

# ---------------------------------------------------------------------------------
# Bills
admin.add_view(BillsView(Bill, db.session, name="Bills", endpoint='bill', frontend_url_format='bill/%s'))

# ---------------------------------------------------------------------------------
# Other Content
admin.add_view(QuestionReplyView(QuestionReply, db.session, name="Questions & Replies", endpoint='question', category="Other Content"))
admin.add_view(CallForCommentView(CallForComment, db.session, name="Calls for Comment", endpoint='call-for-comment', category="Other Content"))
admin.add_view(GazetteView(Gazette, db.session, name="Gazettes", endpoint='gazette', category="Other Content"))
admin.add_view(HansardView(Hansard, db.session, type="plenary", name="Hansards", endpoint='hansard', category="Other Content"))
admin.add_view(PolicyDocumentView(PolicyDocument, db.session, name="Policy Document", endpoint='policy', category="Other Content"))
admin.add_view(DailyScheduleView(DailySchedule, db.session, name="Daily Schedules", endpoint='schedule', category="Other Content"))
admin.add_view(BriefingView(Briefing, db.session, type="media-briefing", name="Media Briefings", endpoint='briefing', category="Other Content"))
admin.add_view(FeaturedContentView(Featured, db.session, category='Other Content', name="Featured Content", endpoint='featured'))
admin.add_view(RedirectView(Redirect, db.session, category='Other Content', name="Legacy Redirects", endpoint='redirects'))
admin.add_view(PageView(Page, db.session, category='Other Content', name="Static Pages", endpoint='pages'))
admin.add_view(FileView(File, db.session, category='Other Content', name="Uploaded Files", endpoint='files'))

# ---------------------------------------------------------------------------------
# Form options
admin.add_view(MyModelView(MembershipType, db.session, name="Membership Type", endpoint='membership-type', category="Form Options"))
admin.add_view(MyModelView(BillStatus, db.session, name="Bill Status", endpoint='bill-status', category="Form Options"))
admin.add_view(MyModelView(BillType, db.session, name="Bill Type", endpoint='bill-type', category="Form Options"))

# ---------------------------------------------------------------------------------
# Email alerts
admin.add_view(EmailAlertView(category='Email Alerts', name="Send Emails", endpoint='alerts'))
admin.add_view(EmailTemplateView(EmailTemplate, db.session, name="Email Templates", category='Email Alerts', endpoint='email-templates'))
