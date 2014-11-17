from app import app, db
from models import *
from flask import Flask, flash, redirect, url_for, request, render_template, g, abort
from flask.ext.admin import Admin, expose, BaseView, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
import urllib
from datetime import datetime
import time
from operator import itemgetter
import logging

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


class MyIndexView(AdminIndexView):
    @expose("/")
    def index(self):

        return self.render('admin/my_index.html')


class MyModelView(ModelView):
    can_create = True
    can_edit = True
    can_delete = False

admin = Admin(app, name='PMG-CMS', base_template='admin/my_base.html', index_view=MyIndexView(name='Home'), template_mode='bootstrap3')

admin.add_view(MyModelView(Organisation, db.session, name="Organisation", endpoint='organisation'))

