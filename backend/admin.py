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
from wtforms import fields, widgets
import urllib
from datetime import datetime
import time
from operator import itemgetter
import logging
from sqlalchemy import func


FRONTEND_HOST = app.config['FRONTEND_HOST']
API_HOST = app.config['API_HOST']
STATIC_HOST = app.config['STATIC_HOST']

logger = logging.getLogger(__name__)

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

        record_counts = {
            'member': Member.query.count(),
            'committee': Organisation.query.filter_by(type="committee").count(),
            'committee-meeting-report': Content.query.filter_by(type="committee-meeting-report").count(),
            }

        return self.render('admin/my_index.html', record_counts=record_counts)


class MyModelView(ModelView):
    can_create = True
    can_edit = True
    can_delete = True
    edit_template = 'admin/my_edit.html'
    create_template = 'admin/my_create.html'
    list_template = 'admin/my_list.html'


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
        'profile_pic_url'
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
    column_searchable_list = ('name', )
    column_formatters = dict(
        profile_pic_url=macro('render_profile_pic'),
        memberships=macro('render_committee_membership')
    )
    form_columns = column_list
    form_overrides = dict(bio=fields.TextAreaField)
    form_ajax_refs = {
        'events': {
            'fields': ('date', 'title', 'type'),
            'page_size': 25
        }
    }


admin = Admin(app, name='PMG-CMS', base_template='admin/my_base.html', index_view=MyIndexView(name='Home'), template_mode='bootstrap3')

admin.add_view(CommitteeView(Organisation, db.session, name="Committee", endpoint='committee', category="Committees"))
admin.add_view(CommitteeMeetingView(CommitteeMeeting, db.session, type="committee-meeting", name="Committee meetings", endpoint='committee-meeting', category="Committees"))

admin.add_view(MemberView(Member, db.session, name="Member", endpoint='member', category="Members"))
admin.add_view(MyModelView(MembershipType, db.session, name="Membership Type", endpoint='membership-type', category="Members"))

