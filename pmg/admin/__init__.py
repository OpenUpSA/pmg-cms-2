import logging
from operator import itemgetter
import datetime
from dateutil.relativedelta import relativedelta

from flask import flash, redirect, url_for, request, make_response
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.babel import gettext
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.filters import BaseSQLAFilter, DateBetweenFilter
from flask.ext.admin.model.form import InlineFormAdmin
from flask.ext.admin.model.template import macro
from flask.ext.admin.form import rules
from flask.ext.admin.helpers import is_form_submitted, get_url
from flask.ext.security.changeable import change_user_password
import flask_wtf
from wtforms import fields
from wtforms.validators import data_required
from sqlalchemy import func
from sqlalchemy.sql.expression import or_
from werkzeug import secure_filename
from jinja2 import Markup
import humanize
import psycopg2

from pmg import app, db
from pmg.models import *  # noqa
from xlsx import XLSXBuilder
from .email_alerts import EmailAlertView
from .rbac import RBACMixin
import widgets

logger = logging.getLogger(__name__)


SAST = psycopg2.tz.FixedOffsetTimezone(offset=120, name=None)


# Our base form extends flask_wtf.Form to get CSRF support,
# and adds the _obj property required by Flask Admin
class BaseForm(flask_wtf.Form):
    def __init__(self, formdata=None, obj=None, prefix=u'', **kwargs):
        self._obj = obj
        super(BaseForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)


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
        cutoff = datetime.datetime.utcnow() - relativedelta(months=months)
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
        today = datetime.date.today()
        tmp = str(months) + " month up to " + str(today)
        if months > 1:
            tmp = str(months) + " months up to " + str(today)
        filename = "PMG active organisations - " + tmp + ".xlsx"
        return self.xlsx(self.get_list(months), filename=filename)


class MyModelView(RBACMixin, ModelView):
    form_base_class = BaseForm

    required_roles = ['editor']

    can_create = True
    can_edit = True
    can_delete = True
    edit_template = 'admin/my_edit.html'
    create_template = 'admin/my_create.html'
    list_template = 'admin/my_list.html'

    def frontend_url(self, model):
        if hasattr(model, 'url') and model.id is not None:
            return model.url
        return None

    def alert_url(self, model):
        """ If we support sending an email alert about this model, what's the URL? """
        if model.id and hasattr(model, 'alert_template'):
            template = model.alert_template
            if template:
                params = {}
                params[model.resource_content_type + "_id"] = model.id
                params["template_id"] = template.id
                params["committee_ids"] = model.committee_id
                params["prefill"] = "1"
                return url_for('alerts.new', **params)


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
                .filter(self.column < datetime.date.today())\
                .filter(self.column != None)  # noqa

        elif value == 'unexpired':
            return query.filter(or_(
                self.column == None,  # noqa
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

    def on_model_change(self, form, model):
        if model.organisation:
            model.expiry = model.organisation.expiry

    @expose('/reset_password', methods=['GET', 'POST'])
    def reset_user_password(self):
        user = User.query.get(request.args['model_id'])
        new_pwd = request.form['new_password']
        return_url = request.headers['Referer']

        if user is None:
            flash(gettext('User not found. Please try again.'), 'error')
            return redirect(return_url)

        if len(new_pwd) < 6:
            flash(gettext(
                'A password must contain at least 6 characters. Please try again.'), 'error')
            return redirect(return_url)

        if ' ' in new_pwd:
            flash(gettext('Passwords cannot contain spaces. Please try again.'), 'error')
            return redirect(return_url)

        change_user_password(user, new_pwd)
        db.session.commit()

        flash(gettext('The password has been changed successfully. A notification has been sent to %s.' % user.email))
        return redirect(return_url)


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
    can_delete = False

    column_list = (
        'name',
        'house',
        'ad_hoc',
        'memberships'
    )
    column_labels = {
        'memberships': 'Members',
        'minister': 'Associated Minister',
    }
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
        'minister',
        'about',
        'contact_details',
        'memberships',
    )
    form_widget_args = {
        'about': {'class': 'ckeditor'},
        'contact_details': {'class': 'ckeditor'},
    }
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
            model.date = model.date.replace(tzinfo=SAST)

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


class InlineCommitteeMeetingAttendance(InlineFormAdmin):
    form_columns = (
        'id',
        'member',
        'attendance',
        'chairperson',
        'alternate_member',
    )
    form_ajax_refs = {
        'member': {
            'fields': ('name',),
            'page_size': 25
        }
    }
    form_choices = {
        'attendance': [
            ('A', 'A - Absent'),
            ('AP', 'AP - Absent with Apologies'),
            ('DE', 'DE - Departed Early'),
            ('L', 'AL - Arrived Late'),
            ('LDE', 'LDE - Arrived Late and Departed Early'),
            ('P', 'P - Present'),
            ('U', 'U - Unknown'),
        ]
    }


class CommitteeMeetingView(EventView):
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
        'actual_start_time',
        'actual_end_time',
        'chairperson',
        'featured',
        'public_participation',
        'bills',
        'summary',
        'body',
        'files',
    )
    form_args = {
        'summary': {'default': '<p>Report of the meeting to follow.</p>'},
        'committee': {'validators': [data_required()]},
        'files': {'widget': widgets.InlineFileWidget()},
    }
    form_widget_args = {
        'body': {'class': 'ckeditor'},
        'summary': {'class': 'ckeditor'}
    }
    form_ajax_refs = {
        'bills': {
            'fields': ('title',),
            'page_size': 50
        }
    }
    inline_models = [
        InlineFile(EventFile),
        InlineCommitteeMeetingAttendance(CommitteeMeetingAttendance),
    ]

    def on_model_change(self, form, model, is_created):
        super(CommitteeMeetingView, self).on_model_change(form, model, is_created)
        # make sure the new times are timezone aware
        for attr in ['actual_start_time', 'actual_end_time']:
            if getattr(model, attr):
                setattr(model, attr, getattr(model, attr).replace(tzinfo=SAST))


class HansardView(EventView):
    column_list = (
        'house',
        'title',
        'date',
    )
    column_sortable_list = (
        'title',
        'house',
        'date',
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', )
    form_columns = (
        'date',
        'house',
        'title',
        'bills',
        'body',
        'files',
    )
    form_args = {
        'house': {'validators': [data_required()]},
    }
    form_widget_args = {
        'body': {'class': 'ckeditor'},
    }
    form_ajax_refs = {
        'bills': {
            'fields': ('title',),
            'page_size': 50
        }
    }
    inline_models = [InlineFile(EventFile)]


class BriefingView(EventView):
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
        'summary': {'class': 'ckeditor'},
        'body': {'class': 'ckeditor'},
    }
    inline_models = [InlineFile(EventFile)]


class MemberView(MyModelView):
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


class CommitteeQuestionView(MyModelView):
    list_template = 'admin/committee_question_list.html'
    create_template = 'admin/committee_question_create.html'

    column_list = (
        'code',
        'committee',
        'question_number',
        'date',
    )
    column_default_sort = ('date', True)
    column_searchable_list = ('code',)
    form_columns = (
        'code',
        'date',
        'intro',
        'question',
        'asked_by_name',
        'asked_by_member',
        'question_to_name',
        'committee',
        'answer',
        'source_file',
        'written_number',
        'oral_number',
        'president_number',
        'deputy_president_number',
    )
    column_labels = {
        'question_to_name': "Question To",
        'committee': "Question To Committee",
    }
    form_args = {
        'files': {'widget': widgets.InlineFileWidget()},
    }
    form_widget_args = {
        'answer': {'class': 'ckeditor'},
    }
    form_ajax_refs = {
        'source_file': {
            'fields': ('title', 'file_path'),
            'page_size': 10,
        },
        'asked_by_member': {
            'fields': ('name',),
            'page_size': 25
        },
    }
    inline_models = [InlineFile(CommitteeQuestionFile)]

    @expose('/upload', methods=['POST'])
    def upload(self):
        return_url = request.headers['Referer']
        file_data = request.files.get('file')
        try:
            question = CommitteeQuestion.import_from_uploaded_answer_file(file_data)
            if question.id:
                # it already existed
                flash("That question has already been imported.", "warn")
                return redirect(get_url('.edit_view', id=question.id, url=return_url))

            db.session.add(question)
            db.session.commit()
            flash("Successfully imported from %s" % (file_data.filename,))
            return redirect(get_url('.edit_view', id=question.id, url=return_url))
        except ValueError as e:
            flash("Couldn't import from %s: %s" % (file_data.filename, e.message), 'error')
            return redirect(return_url)

    def frontend_url(self, model):
        if model.id and model.committee:
            return url_for('committee_question', question_id=model.id)
        return None


class QuestionReplyView(MyModelView):
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
        'body': {'class': 'ckeditor'},
    }
    inline_models = [InlineFile(QuestionReplyFile)]


class CallForCommentView(MyModelView):
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
        'body': {'class': 'ckeditor'},
    }


class DailyScheduleView(ViewWithFiles, MyModelView):
    column_exclude_list = (
        'body',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
    }
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(DailyScheduleFile)]


class GazetteView(ViewWithFiles, MyModelView):
    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(GazetteFile)]


class PolicyDocumentView(ViewWithFiles, MyModelView):
    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = [InlineFile(PolicyDocumentFile)]


class TabledCommitteeReportView(ViewWithFiles, MyModelView):
    column_exclude_list = (
        'body',
        'summary',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {'class': 'ckeditor'},
        'summary': {'class': 'ckeditor'},
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
        'body': {'class': 'ckeditor'},
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
        model.date = model.date.replace(tzinfo=SAST)


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


class MinisterView(MyModelView):
    column_list = (
        'name',
    )
    column_default_sort = ('name', True)
    column_searchable_list = ('name',)
    form_columns = (
        'name',
    )


class FeaturedContentView(MyModelView):
    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        model.start_date = model.start_date.replace(tzinfo=SAST)


class FileView(MyModelView):
    column_list = ('title', 'file_path', 'file_bytes')
    column_searchable_list = ('title', 'file_path')
    column_default_sort = 'file_path'
    column_labels = {'file_bytes': 'Size'}
    column_formatters = {
        'file_bytes': lambda v, c, m, n: '-' if m.file_bytes is None else Markup('<nobr>%s</nobr>' % humanize.naturalsize(m.file_bytes)),
    }

    class SizeRule(rules.BaseRule):
        def __call__(self, form, form_opts=None, field_args={}):
            return humanize.naturalsize(form.file_bytes.data) if form.file_bytes.data else '-'

    class UrlRule(rules.BaseRule):
        def __call__(self, form, form_opts=None, field_args={}):
            url = url_for('docs', path=form.file_path.data)
            return Markup(
                '<a href="%s" target="_blank">%s</a>' % (url, url)
            )

    form_columns = (
        'title',
        'description',
        'file_path',
        'file_mime',
        'file_bytes',
    )
    form_widget_args = {
        'file_mime': {'readonly': True},
        'file_path': {'readonly': True},
        'file_bytes': {'readonly': True},
    }

    form_edit_rules = [
        'title', 'description', 'file_path', 'file_mime',
        rules.Container('rules.staticfield', SizeRule(), label='Size'),
        rules.Container('rules.staticfield', UrlRule(), label='URL'),
    ]

    form_create_rules = ['title', 'description', 'upload']

    def get_create_form(self):
        # allow user to upload a file when creating form
        form = super(FileView, self).get_create_form()
        form.upload = fields.FileField('Upload a file', [data_required()])
        return form

    def validate_form(self, form):
        if is_form_submitted():
            if hasattr(form, 'upload') and request.files.get(form.upload.name):
                file_data = request.files.get(form.upload.name)
                # ensures validation works, will be overwritten
                form.file_path.raw_data = secure_filename(file_data.filename)
        return super(FileView, self).validate_form(form)

    def on_model_change(self, form, model, is_create):
        if is_create:
            file_data = request.files.get(form.upload.name)
            model.from_upload(file_data)


class RedirectView(MyModelView):
    column_list = ('old_url', 'new_url', 'nid')
    column_searchable_list = ('old_url', 'new_url')
    column_default_sort = 'old_url'


class PageView(ViewWithFiles, MyModelView):
    column_list = ('slug', 'title')
    column_searchable_list = ('slug', 'title')
    column_default_sort = 'slug'

    form_columns = ('title', 'slug', 'path', 'body', 'show_files', 'files')
    form_extra_fields = {
        'path': fields.TextField('Path'),
    }
    form_widget_args = {
        'body': {'class': 'ckeditor'},
        'path': {'readonly': True},
    }
    inline_models = [InlineFile(PageFile)]
    column_descriptions = {
        'show_files': 'Show a list of the files attached to this page in a box on the right?',
    }

    def frontend_url(self, model):
        return '/page/%s' % model.slug

    def on_form_prefill(self, form, id):
        super(PageView, self).on_form_prefill(form, id)
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
admin.add_view(CallForCommentView(CallForComment, db.session, name="Calls for Comment", endpoint='call-for-comment', category="Committees"))
admin.add_view(CommitteeQuestionView(CommitteeQuestion, db.session, name="Questions to Committees", endpoint='committee-question', category="Committees"))
admin.add_view(MinisterView(Minister, db.session, name="Ministers", endpoint='minister', category="Committees"))
admin.add_view(QuestionReplyView(QuestionReply, db.session, name="Old Questions & Replies", endpoint='question', category="Committees"))
admin.add_view(TabledCommitteeReportView(TabledCommitteeReport, db.session, name="Tabled Committee Reports", endpoint='tabled-committee-report', category="Committees"))

# ---------------------------------------------------------------------------------
# Bills
admin.add_view(BillsView(Bill, db.session, name="Bills", endpoint='bill'))

# ---------------------------------------------------------------------------------
# Other Content
admin.add_view(DailyScheduleView(DailySchedule, db.session, name="Daily Schedules", endpoint='schedule', category="Other Content"))
admin.add_view(FeaturedContentView(Featured, db.session, name="Featured Content", endpoint='featured', category="Other Content"))
admin.add_view(GazetteView(Gazette, db.session, name="Gazettes", endpoint='gazette', category="Other Content"))
admin.add_view(HansardView(Hansard, db.session, type="plenary", name="Hansards", endpoint='hansard', category="Other Content"))
admin.add_view(BriefingView(Briefing, db.session, type="media-briefing", name="Media Briefings", endpoint='briefing', category="Other Content"))
admin.add_view(RedirectView(Redirect, db.session, category='Other Content', name="Legacy Redirects", endpoint='redirects'))
admin.add_view(PolicyDocumentView(PolicyDocument, db.session, name="Policy Document", endpoint='policy', category="Other Content"))
admin.add_view(PageView(Page, db.session, category='Other Content', name="Static Pages", endpoint='pages'))
admin.add_view(FileView(File, db.session, category='Other Content', name="Uploaded Files", endpoint='files'))

# ---------------------------------------------------------------------------------
# Form options
admin.add_view(MyModelView(BillStatus, db.session, name="Bill Status", endpoint='bill-status', category="Form Options"))
admin.add_view(MyModelView(BillType, db.session, name="Bill Type", endpoint='bill-type', category="Form Options"))
admin.add_view(MyModelView(MembershipType, db.session, name="Membership Type", endpoint='membership-type', category="Form Options"))

# ---------------------------------------------------------------------------------
# Email alerts
admin.add_view(EmailAlertView(category='Email Alerts', name="Send Emails", endpoint='alerts'))
admin.add_view(EmailTemplateView(EmailTemplate, db.session, name="Email Templates", category='Email Alerts', endpoint='email-templates'))

# ---------------------------------------------------------------------------------
# Members
admin.add_view(MemberView(Member, db.session, name="Members", endpoint='member'))
