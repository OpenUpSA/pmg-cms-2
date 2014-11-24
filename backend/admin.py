from app import app, db
from models import *
from flask import Flask, flash, redirect, url_for, request, render_template, g, abort
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
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

logger = logging.getLogger(__name__)

@app.context_processor
def inject_paths():
    return dict(FRONTEND_HOST=FRONTEND_HOST)

@app.template_filter('add_commas')
def jinja2_filter_add_commas(quantity):
    out = ""
    quantity_str = str(quantity)
    while len(quantity_str) > 3:
        tmp = quantity_str[-3::]
        out = "," + tmp + out
        quantity_str = quantity_str[0:-3]
    return quantity_str + out


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


class CommitteeView(MyModelView):

    form_ajax_refs = {
        'events': {
            'fields': ('date', 'title', 'type'),
            'page_size': 25
        }
    }
    column_list = ('name', 'house')
    column_sortable_list = ('name', ('house', 'house.name'))
    column_searchable_list = ('name', )
    form_columns = ('name', 'house')

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


class ContentView(MyModelView):

    form_overrides = dict(body=CKTextAreaField)
    form_excluded_columns = ('type', 'version', 'title', 'file_path')
    column_exclude_list = ('type', 'version', 'title', 'file_path')
    form_widget_args = {
        'body': {
            'class': 'ckeditor'
        },
        'summary': {
            'class': 'ckeditor'
        }
    }
    form_ajax_refs = {
        'event': {
            'fields': ('date', 'title', 'type'),
            'page_size': 25
        }
    }
    column_formatters = dict(
        body=macro('render_raw_html'),
        summary=macro('render_raw_html'),
        )

    def __init__(self, model, session, **kwargs):
        self.type = kwargs.pop('type')
        super(ContentView, self).__init__(model, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            # set some default values when creating a new record
            model.type = self.content_type
            model.version = 0

    def get_query(self):
        """
        Add filter to return only non-deleted records.
        """

        return self.session.query(self.model) \
            .filter(self.model.type == self.type)

    def get_count_query(self):
        """
        Add filter to count only non-deleted records.
        """

        return self.session.query(func.count('*')).select_from(self.model) \
            .filter(self.model.type == self.type)


class MemberView(MyModelView):

    column_list = (
        'name',
        'house',
        'party',
        'province',
        'bio',
        'profile_pic_url'
    )
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
admin.add_view(ContentView(Content, db.session, type="committee-meeting-report", name="Meeting reports", endpoint='committee-meeting-report', category="Committees"))

admin.add_view(MemberView(Member, db.session, name="Member", endpoint='member', category="Members"))
admin.add_view(MyModelView(Membership, db.session, name="Membership", endpoint='membership', category="Members"))
admin.add_view(MyModelView(MembershipType, db.session, name="Membership Type", endpoint='membership-type', category="Members"))

