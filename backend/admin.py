import logging
import os
from operator import itemgetter
import datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta

from flask import Flask, flash, redirect, url_for, request, render_template, g, abort, make_response
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.form import RenderTemplateWidget
from flask.ext.admin.model.form import InlineFormAdmin
from flask.ext.admin.contrib.sqla.form import InlineModelConverter
from flask.ext.admin.contrib.sqla.fields import InlineModelFormList
from flask.ext.admin.model.template import macro
from flask.ext.security import current_user
from wtforms import fields, widgets
from sqlalchemy import func
from werkzeug import secure_filename
from s3_upload import S3Bucket
from xlsx import XLSXBuilder
from app import app, db
from models import *
from email_alerts import EmailAlertView
from rbac import RBACMixin


FRONTEND_HOST = app.config['FRONTEND_HOST']
API_HOST = app.config['API_HOST']
STATIC_HOST = app.config['STATIC_HOST']
UPLOAD_PATH = app.config['UPLOAD_PATH']
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']

s3_bucket = S3Bucket()
logger = logging.getLogger(__name__)

if not os.path.isdir(UPLOAD_PATH):
    os.mkdir(UPLOAD_PATH)


def allowed_file(filename):
    logger.debug(filename)
    tmp = '.' in filename and \
          filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    logger.debug(tmp)
    return tmp


@app.context_processor
def inject_paths():
    context_vars = {
        'FRONTEND_HOST': FRONTEND_HOST,
        'API_HOST': API_HOST,
        'STATIC_HOST': STATIC_HOST,
        }
    return context_vars


@app.template_filter('add_commas')
def jinja2_filter_add_commas(quantity):
    out = ""
    quantity_str = str(quantity)
    while len(quantity_str) > 3:
        tmp = quantity_str[-3::]
        out = "," + tmp + out
        quantity_str = quantity_str[0:-3]
    return quantity_str + out


@app.template_filter('dir')
def jinja2_filter_dir(value):
    res = []
    for k in dir(value):
        res.append('%r %r\n' % (k, getattr(value, k)))
    return '<br>'.join(res)


@app.template_filter('is_file')
def jinja2_filter_is_file(content_obj):
    logger.debug("IS_FILE")
    logger.debug(content_obj)
    if content_obj.file:
        return True
    return False


# Define wtforms widget and field
class CKTextAreaWidget(widgets.TextArea):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(fields.TextAreaField):
    widget = CKTextAreaWidget()


class MyIndexView(RBACMixin, AdminIndexView):
    required_roles = ['editor']

    @expose("/")
    def index(self):

        record_counts = [
            ('Members', 'member.index_view', Member.query.count()),
            ('Bill', 'bill.index_view', Bill.query.count()),
            ('Committee', 'committee.index_view', Committee.query.count()),
            ('Committee Meetings', 'committee_meeting.index_view', Event.query.filter_by(type="committee-meeting").count()),
            ('Questions & Replies', 'question.index_view', QuestionReply.query.count()),
            ('Calls for Comment', 'call_for_comment.index_view', CallForComment.query.count()),
            ('Daily Schedules', 'schedule.index_view', DailySchedule.query.count()),
            ('Gazette', 'gazette.index_view', Gazette.query.count()),
            ('Hansards', 'hansard.index_view', Event.query.filter_by(type="plenary").count()),
            ('Media Briefings', 'briefing.index_view', Event.query.filter_by(type="media-briefing").count()),
            ('Policy Documents', 'policy.index_view', PolicyDocument.query.count()),
            ('Tabled Committee Reports', 'tabled_report.index_view', TabledCommitteeReport.query.count()),
            ]
        record_counts = sorted(record_counts, key=itemgetter(2), reverse=True)
        file_count = Content.query.count()

        return self.render(
            'admin/my_index.html',
            record_counts=record_counts,
            file_count=file_count)


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
            return FRONTEND_HOST + self.frontend_url_format % self.get_pk_value(model)
        return None


class UserView(MyModelView):
    required_roles = ['user-admin']

    can_create = False
    can_delete = True
    column_list = [
        'email',
        'active',
        'confirmed_at',
        'current_login_at',
        'login_count',
        ]
    column_labels = {'current_login_at': "Last seen"}
    column_formatters = {'current_login_at': macro("datetime_as_date")}
    column_searchable_list = ('email',)
    form_excluded_columns = [
        'password',
        'confirmed_at',
        'last_login_at',
        'current_login_at',
        'last_login_ip',
        'current_login_ip',
        'login_count',
        ]


class OrganisationView(MyModelView):

    can_create = True
    column_searchable_list = ('domain', 'name')
    form_ajax_refs = {
        'users': {
            'fields': ('name', 'email'),
            'page_size': 25
        },
        'subscriptions': {
            'fields': ('name', ),
            'page_size': 25
        }
    }
    form_excluded_columns = [
        'created_at',
        ]

    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        model.expiry = model.expiry.replace(tzinfo=tz.tzlocal())


# This widget uses custom template for inline field list
class InlineMembershipsWidget(RenderTemplateWidget):

    def __init__(self):
        super(
            InlineMembershipsWidget,
            self).__init__('admin/inline_membership.html')


# This InlineModelFormList will use our custom widget, when creating a
# list of forms
class MembershipsFormList(InlineModelFormList):
    widget = InlineMembershipsWidget()


# Create custom InlineModelConverter to link the form to its model
class MembershipModelConverter(InlineModelConverter):
    inline_field_list_type = MembershipsFormList


class CommitteeView(MyModelView):
    frontend_url_format = 'committee/%s'

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
    inline_models = (Membership, )
    inline_model_form_converter = MembershipModelConverter


class EventView(MyModelView):

    form_excluded_columns = ('type', )
    column_exclude_list = ('type', )

    form_ajax_refs = {
        'content': {
            'fields': ('type', ),
            'page_size': 25
        }
    }

    def __init__(self, model, session, **kwargs):
        self.type = kwargs.pop('type')
        super(EventView, self).__init__(model, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            # set some default values when creating a new record
            model.type = self.type
        # make sure the new date is timezone aware
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


# This widget uses custom template for inline field list
class InlineContentWidget(RenderTemplateWidget):

    def __init__(self):
        super(InlineContentWidget, self).__init__('admin/inline_content.html')


# This InlineModelFormList will use our custom widget, when creating a
# list of forms
class ContentFormList(InlineModelFormList):
    widget = InlineContentWidget()


# Create custom InlineModelConverter to link the form to its model
class ContentModelConverter(InlineModelConverter):
    inline_field_list_type = ContentFormList


class InlineContent(InlineFormAdmin):
    form_excluded_columns = ('type', 'file', 'rich_text')

    def postprocess_form(self, form_class):
        # add a field for handling the file upload
        form_class.upload = fields.FileField('File')
        form_class.title = fields.StringField('Title')
        return form_class

    def on_model_change(self, form, model):
        # save file, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            if not allowed_file(file_data.filename):
                raise Exception("File type not allowed.")
            # create file object
            new_file = File(file_mime=file_data.content_type)
            new_file.title = form.title.data
            filename = secure_filename(file_data.filename)
            # save file to disc
            logger.debug('saving uploaded file: ' + filename)
            file_data.save(os.path.join(UPLOAD_PATH, filename))
            # upload saved file to S3
            filename = s3_bucket.upload_file(filename)
            new_file.file_path = filename
            # set relation between content model and file model
            model.file = new_file
            model.type = "related-doc"
            db.session.add(new_file)


class CommitteeMeetingView(EventView):
    frontend_url_format = 'committee-meeting/%d'

    column_list = ('date', 'title', 'committee', 'content')
    column_labels = {'committee': 'Committee', }
    column_sortable_list = (
        'date',
        ('committee', 'committee.name'),
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('committee.name', 'title')
    column_formatters = dict(
        content=macro('render_event_content'),
        )
    form_excluded_columns = (
        'event',
        'member',
    )
    form_columns = (
        'committee',
        'title',
        'date',
        'chairperson',
        'summary',
        'body',
        'content',
    )
    form_extra_fields = {
        'summary': CKTextAreaField('Summary'),
        'body': CKTextAreaField('Body'),
        }
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        'summary': {
            'class': 'ckeditor'
        }
    }
    inline_models = (
        InlineContent(Content),
    )
    inline_model_form_converter = ContentModelConverter

    def on_form_prefill(self, form, id):
        event_obj = Event.query.get(id)
        committee_meeting_report = Content.query.filter_by(event=event_obj).filter_by(type="committee-meeting-report").one()

        form.summary.data = committee_meeting_report.rich_text.summary
        form.body.data = committee_meeting_report.rich_text.body
        return

    def on_model_change(self, form, model, is_created):
        # create / update related CommitteeMeetingReport
        if is_created:
            rich_text_obj = RichText()
            db.session.add(rich_text_obj)
            committee_meeting_report = Content(event=model, type="committee-meeting-report", rich_text=rich_text_obj)
        else:
            committee_meeting_report = Content.query.filter_by(event=model).filter_by(type="committee-meeting-report").one()
            rich_text_obj = committee_meeting_report.rich_text
        rich_text_obj.summary = form.summary.data
        rich_text_obj.body = form.body.data
        db.session.add(committee_meeting_report)
        db.session.add(rich_text_obj)
        return super(CommitteeMeetingView, self).on_model_change(form, model, is_created)


class HansardView(EventView):
    frontend_url_format = 'hansard/%d'

    column_list = (
        'title',
        'date',
        'content',
    )
    column_sortable_list = (
        'title',
        'date',
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', )
    column_formatters = dict(
        content=macro('render_event_content'),
        )
    form_excluded_columns = (
        'event',
        'member',
    )
    form_columns = (
        'date',
        'body',
        'content',
    )
    form_extra_fields = {
        'body': CKTextAreaField('Body'),
        }
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        }
    inline_models = (
        InlineContent(Content),
    )
    inline_model_form_converter = ContentModelConverter

    def on_form_prefill(self, form, id):
        event_obj = Event.query.get(id)
        hansard = Content.query.filter_by(event=event_obj).filter_by(type="hansard").one()
        if hansard.rich_text:
            form.body.data = hansard.rich_text.body
        return

    def on_model_change(self, form, model, is_created):
        # create / update related Hansard content record
        if is_created:
            rich_text_obj = RichText()
            db.session.add(rich_text_obj)
            hansard = Content(event=model, type="hansard", rich_text=rich_text_obj)
        else:
            hansard = Content.query.filter_by(event=model).filter_by(type="hansard").one()
            rich_text_obj = hansard.rich_text
        rich_text_obj.body = form.body.data
        db.session.add(hansard)
        db.session.add(rich_text_obj)
        return super(HansardView, self).on_model_change(form, model, is_created)


class BriefingView(EventView):
    frontend_url_format = 'briefing/%s'

    column_list = (
        'committee',
        'title',
        'date',
        'content',
    )
    column_sortable_list = (
        'title',
        'date',
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', )
    column_formatters = dict(
        content=macro('render_event_content'),
        )
    form_excluded_columns = (
        'event',
        'member',
    )
    form_columns = (
        'committee',
        'date',
        'summary',
        'body',
        'content',
    )
    form_extra_fields = {
        'summary': CKTextAreaField('Summary'),
        'body': CKTextAreaField('Body'),
        }
    form_widget_args = {
        'summary': {
            'class': 'ckeditor'
        },
        'body': {
            'class': 'ckeditor'
        },
        }
    inline_models = (
        InlineContent(Content),
    )
    inline_model_form_converter = ContentModelConverter

    def on_form_prefill(self, form, id):
        event_obj = Event.query.get(id)
        briefing = Content.query.filter_by(event=event_obj).filter_by(type="briefing").one()
        if briefing.rich_text:
            form.summary.data = briefing.rich_text.summary
            form.body.data = briefing.rich_text.body
        return

    def on_model_change(self, form, model, is_created):
        # create / update related briefing content record
        if is_created:
            rich_text_obj = RichText()
            db.session.add(rich_text_obj)
            briefing = Content(event=model, type="briefing", rich_text=rich_text_obj)
        else:
            briefing = Content.query.filter_by(event=model).filter_by(type="briefing").one()
            rich_text_obj = briefing.rich_text
        rich_text_obj.summary = form.summary.data
        rich_text_obj.body = form.body.data
        db.session.add(briefing)
        db.session.add(rich_text_obj)
        return super(BriefingView, self).on_model_change(form, model, is_created)



class MemberView(MyModelView):
    frontend_url_format = 'member/%d'

    column_list = (
        'name',
        'house',
        'party',
        'province',
        'memberships',
        'bio',
        'pa_link',
        'profile_pic_url',
    )
    column_labels = {'memberships': 'Committees', }
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
    form_columns = (
        'name',
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

    def on_model_change(self, form, model):
        # save profile pic, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            if not allowed_file(file_data.filename):
                raise Exception("File type not allowed.")
            filename = secure_filename(file_data.filename)
            logger.debug('saving uploaded file: ' + filename)
            file_data.save(os.path.join(UPLOAD_PATH, filename))
            filename = s3_bucket.upload_file(filename)
            model.profile_pic_url = filename


# This widget uses custom template for inline field list
class InlineFileWidget(RenderTemplateWidget):

    def __init__(self):
        super(InlineFileWidget, self).__init__('admin/inline_file.html')


# This InlineModelFormList will use our custom widget, when creating a
# list of forms
class FileFormList(InlineModelFormList):
    widget = InlineFileWidget()


# Create custom InlineModelConverter to link the form to its model
class FileModelConverter(InlineModelConverter):
    inline_field_list_type = FileFormList


class InlineFile(InlineFormAdmin):
    form_excluded_columns = (
        'title',
        'file_mime',
        'origname',
        'description',
        'duration',
        'playtime',
        'file_path',
        'daily_schedule',
        'gazette',
        'tabled_committee_report',
        'policy_document',
    )

    def postprocess_form(self, form_class):
        # add a field for handling the file upload
        form_class.upload = fields.FileField('File')
        return form_class

    def on_model_change(self, form, model):
        # save file, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            if not allowed_file(file_data.filename):
                raise Exception("File type not allowed.")
            # create file object
            model.file_mime=file_data.mimetype
            filename = secure_filename(file_data.filename)
            # save file to disc
            logger.debug('saving uploaded file: ' + filename)
            file_data.save(os.path.join(UPLOAD_PATH, filename))
            # upload saved file to S3
            filename = s3_bucket.upload_file(filename)
            model.file_path = filename



class QuestionReplyView(MyModelView):
    frontend_url_format = 'question_reply/%d'

    column_exclude_list = (
        'body',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', 'question_number')
    form_excluded_columns = ('nid', )
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        }


class CallForCommentView(MyModelView):
    frontend_url_format = 'call-for-comment/%s'

    column_exclude_list = (
        'body',
        'summary',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        'summary': {
            'class': 'ckeditor'
        },
        }


class DailyScheduleView(MyModelView):
    frontend_url_format = 'daily_schedule/%d'

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
    inline_models = (
        InlineFile(File),
    )
    inline_model_form_converter = FileModelConverter


class GazetteView(MyModelView):
    frontend_url_format = 'gazette/%d'

    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = (
        InlineFile(File),
    )
    inline_model_form_converter = FileModelConverter


class PolicyDocumentView(MyModelView):
    frontend_url_format = 'policy-document/%d'

    column_default_sort = ('effective_date', True)
    column_searchable_list = ('title', )
    form_excluded_columns = ('nid', )
    inline_models = (
        InlineFile(File),
    )
    inline_model_form_converter = FileModelConverter


class TabledReportView(MyModelView):
    frontend_url_format = 'tabled-committee-report/%d'

    column_exclude_list = (
        'body',
        'summary',
    )
    column_default_sort = ('start_date', True)
    column_searchable_list = ('title', )
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        'summary': {
            'class': 'ckeditor'
        },
        }
    form_excluded_columns = ('nid', )
    inline_models = (
        InlineFile(File),
    )
    inline_model_form_converter = FileModelConverter


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
        'body': {
            'class': 'ckeditor'
        },
        }

# initialise admin instance
admin = Admin(
    app,
    name='PMG-CMS',
    base_template='admin/my_base.html',
    index_view=MyIndexView(
        name='Home'),
    template_mode='bootstrap3')

# usage reports
admin.add_view(
    UsageReportView(
        name="Usage report",
        endpoint='usage_report',
        category='Users'))

# add admin views for each model
admin.add_view(
    UserView(
        User,
        db.session,
        name="Users",
        endpoint='user',
        category='Users'))
admin.add_view(
    OrganisationView(
        Organisation,
        db.session,
        name="Organisations",
        endpoint='organisation',
        category='Users'))
admin.add_view(
    CommitteeView(
        Committee,
        db.session,
        name="Committees",
        endpoint='committee',
        category="Committees"))
admin.add_view(
    CommitteeMeetingView(
        CommitteeMeeting,
        db.session,
        type="committee-meeting",
        name="Committee Meetings",
        endpoint='committee_meeting',
        category="Committees"))
admin.add_view(
    TabledReportView(
        TabledCommitteeReport,
        db.session,
        name="Tabled Committee Reports",
        endpoint='tabled_report',
        category="Committees"))
admin.add_view(
    MemberView(
        Member,
        db.session,
        name="Members",
        endpoint='member'))
admin.add_view(
    MyModelView(
        Bill,
        db.session,
        name="Bills",
        endpoint='bill',
        frontend_url_format='bill/%s'))
admin.add_view(
    QuestionReplyView(
        QuestionReply,
        db.session,
        name="Questions & Replies",
        endpoint='question',
        category="Other Content"))
admin.add_view(
    CallForCommentView(
        CallForComment,
        db.session,
        name="Calls for Comment",
        endpoint='call_for_comment',
        category="Other Content"))
admin.add_view(
    GazetteView(
        Gazette,
        db.session,
        name="Gazettes",
        endpoint='gazette',
        category="Other Content"))
admin.add_view(
    HansardView(
        Event,
        db.session,
        type="plenary",
        name="Hansards",
        endpoint='hansard',
        category="Other Content"))
admin.add_view(
    PolicyDocumentView(
        PolicyDocument,
        db.session,
        name="Policy Document",
        endpoint='policy',
        category="Other Content"))
admin.add_view(
    DailyScheduleView(
        DailySchedule,
        db.session,
        name="Daily Schedules",
        endpoint='schedule',
        category="Other Content"))
admin.add_view(
    BriefingView(
        Event,
        db.session,
        type="media-briefing",
        name="Media Briefings",
        endpoint='briefing',
        category="Other Content"))
admin.add_view(
    MyModelView(
        MembershipType,
        db.session,
        name="Membership Type",
        endpoint='membership-type',
        category="Form Options"))
admin.add_view(
    MyModelView(
        BillStatus,
        db.session,
        name="Bill Status",
        endpoint='bill-status',
        category="Form Options"))
admin.add_view(
    MyModelView(
        BillType,
        db.session,
        name="Bill Type",
        endpoint='bill-type',
        category="Form Options"))

# Email alerts
admin.add_view(
    EmailAlertView(
        category='Email Alerts',
        name="Send Emails",
        endpoint='alerts'))
admin.add_view(
    EmailTemplateView(
        EmailTemplate,
        db.session,
        name="Email Templates",
        category='Email Alerts',
        endpoint='email-templates'))
