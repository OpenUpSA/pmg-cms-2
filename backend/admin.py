from app import app, db
from models import *
from flask import Flask, flash, redirect, url_for, request, render_template, g, abort
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.form import RenderTemplateWidget
from flask.ext.admin.model.form import InlineFormAdmin
from flask.ext.admin.contrib.sqla.form import InlineModelConverter
from flask.ext.admin.contrib.sqla.fields import InlineModelFormList
from flask.ext.admin.model.template import macro
from flask.ext.security import current_user
from wtforms import fields, widgets
import logging
from sqlalchemy import func
from werkzeug import secure_filename
import os
from s3_upload import S3Bucket
import urllib



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


# Define wtforms widget and field
class CKTextAreaWidget(widgets.TextArea):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(fields.TextAreaField):
    widget = CKTextAreaWidget()


class MyIndexView(AdminIndexView):
    @expose("/")
    def index(self):

        record_counts = [
            ('Members', Member.query.count()),
            ('Committee', Organisation.query.filter_by(type="committee").count()),
            ('Committee Meetings', CommitteeMeeting.query.count()),
            ('Attachments', Content.query.count()),
            ('Bills', Bill.query.count()),
            ('Questions & Replies', Questions_replies.query.count()),
            ('Calls for Comment', Calls_for_comment.query.count()),
            ('Daily Schedules', Daily_schedule.query.count()),
            ('Gazette', Gazette.query.count()),
            ('Hansards', Hansard.query.count()),
            ('Media Briefings', Briefing.query.count()),
            ('Policy Documents', Policy_document.query.count()),
            ('Tabled Committee Reports', Tabled_committee_report.query.count()),
            ]

        return self.render('admin/my_index.html', record_counts=record_counts)


class MyModelView(ModelView):
    can_create = True
    can_edit = True
    can_delete = True
    edit_template = 'admin/my_edit.html'
    create_template = 'admin/my_create.html'
    list_template = 'admin/my_list.html'

    def is_accessible(self):
        if not current_user.is_active() or not current_user.is_authenticated():
            return False
        if not current_user.has_role('editor'):
            return False
        return True

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            return redirect('/security/login?next=' + urllib.quote_plus(request.url), code=302)


class MyRestrictedModelView(MyModelView):

    def is_accessible(self):
        if not current_user.is_active() or not current_user.is_authenticated():
            return False
        if not current_user.has_role('editor') or not current_user.has_role('user-admin'):
            return False
        return True


class UserView(MyRestrictedModelView):
    can_create = False
    can_delete = True
    column_list = [
        'email',
        'active',
        'confirmed_at',
        'last_login_at',
        'current_login_at',
        'last_login_ip',
        'current_login_ip',
        'login_count',
        ]
    form_excluded_columns = [
        'password',
        'confirmed_at',
        'last_login_at',
        'current_login_at',
        'last_login_ip',
        'current_login_ip',
        'login_count',
        ]


# This widget uses custom template for inline field list
class InlineMembershipsWidget(RenderTemplateWidget):
    def __init__(self):
        super(InlineMembershipsWidget, self).__init__('admin/inline_membership.html')


# This InlineModelFormList will use our custom widget, when creating a list of forms
class MembershipsFormList(InlineModelFormList):
    widget = InlineMembershipsWidget()


# Create custom InlineModelConverter to link the form to its model
class MembershipModelConverter(InlineModelConverter):
    inline_field_list_type = MembershipsFormList


class CommitteeView(MyModelView):

    column_list = (
        'name',
        'house',
        'memberships'
    )
    column_labels = {'memberships': 'Members', }
    column_sortable_list = (
        'name',
        ('house', 'house.name'),
    )
    column_default_sort = (Organisation.name, False)
    column_searchable_list = ('name', )
    column_formatters = dict(
        memberships=macro('render_membership_count'),
        )
    form_columns = (
        'name',
        'house',
        'memberships',
    )
    inline_models = (Membership, )
    inline_model_form_converter = MembershipModelConverter

    def on_model_change(self, form, model, is_created):
        if is_created:
            # set some default values when creating a new record
            model.type = "committee"
            model.version = 0

    def get_query(self):
        """
        Add filter to return only non-deleted records.
        """

        return self.session.query(self.model) \
            .filter(self.model.type == "committee")

    def get_count_query(self):
        """
        Add filter to count only non-deleted records.
        """

        return self.session.query(func.count('*')).select_from(self.model) \
            .filter(self.model.type == "committee")


class EventView(MyModelView):

    form_excluded_columns = ('type', )
    column_exclude_list = ('type', )

    form_ajax_refs = {
        'content': {
            'fields': ('title', 'type'),
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
            model.version = 0

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


# This InlineModelFormList will use our custom widget, when creating a list of forms
class ContentFormList(InlineModelFormList):
    widget = InlineContentWidget()


# Create custom InlineModelConverter to link the form to its model
class ContentModelConverter(InlineModelConverter):
    inline_field_list_type = ContentFormList


class InlineContent(InlineFormAdmin):
    form_excluded_columns = ('type', 'file_path', )

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
            filename = secure_filename(file_data.filename)
            model.type = file_data.content_type
            logger.debug('saving uploaded file: ' + filename)
            file_data.save(os.path.join(UPLOAD_PATH, filename))
            model.file_path = filename
            s3_bucket.upload_file(filename)


class CommitteeMeetingView(EventView):

    # note: the related committee_meeting is displayed as part of the event model
    # by using SQLAlchemy joined-table inheritance. See gist: https://gist.github.com/mrjoes/6007994

    form_excluded_columns = ('type', 'member', )
    column_list = ('date', 'organisation', 'title', 'content')
    column_labels = {'organisation': 'Committee', }
    column_sortable_list = (
        'date',
        'title',
        ('organisation', 'organisation.name'),
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ('title', 'organisation.name')
    column_formatters = dict(
        content=macro('render_event_content'),
        )
    form_excluded_columns = (
        'event',
        'type',
        'version',
        'member',
    )
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


class MemberView(MyModelView):

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
            s3_bucket.upload_file(filename)
            model.profile_pic_url = filename


admin = Admin(app, name='PMG-CMS', base_template='admin/my_base.html', index_view=MyIndexView(name='Home'), template_mode='bootstrap3')
admin.add_view(UserView(User, db.session, name="Users", endpoint='user'))

admin.add_view(CommitteeView(Organisation, db.session, name="Committees", endpoint='committee', category="Committees"))
admin.add_view(CommitteeMeetingView(CommitteeMeeting, db.session, type="committee-meeting", name="Committee Meetings", endpoint='committee-meeting', category="Committees"))
admin.add_view(MyModelView(Tabled_committee_report, db.session, name="Tabled Committee Reports", endpoint='tabled_report', category="Committees"))
admin.add_view(MyModelView(Bill, db.session, name="Bills", endpoint='bill'))

admin.add_view(MemberView(Member, db.session, name="Members", endpoint='member'))
admin.add_view(MyModelView(Questions_replies, db.session, name="Questions & Replies", endpoint='question', category="Other Content"))

admin.add_view(MyModelView(Calls_for_comment, db.session, name="Calls for Comment", endpoint='call_for_comment', category="Other Content"))
admin.add_view(MyModelView(Gazette, db.session, name="Gazettes", endpoint='gazette', category="Other Content"))
admin.add_view(MyModelView(Hansard, db.session, name="Hansards", endpoint='hansard', category="Other Content"))
admin.add_view(MyModelView(Policy_document, db.session, name="Policy Document", endpoint='policy', category="Other Content"))
admin.add_view(MyModelView(Daily_schedule, db.session, name="Daily Schedules", endpoint='schedule', category="Other Content"))
admin.add_view(MyModelView(Briefing, db.session, name="Media Briefings", endpoint='briefing', category="Other Content"))

admin.add_view(MyModelView(MembershipType, db.session, name="Membership Type", endpoint='membership-type', category="Form Options"))
admin.add_view(MyModelView(BillStatus, db.session, name="Bill Status", endpoint='bill-status', category="Form Options"))
admin.add_view(MyModelView(BillType, db.session, name="Bill Type", endpoint='bill-type', category="Form Options"))

