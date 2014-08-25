import drupal_models as models
import json
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.model.template import macro
from app import db, logger, app, model_dict
import datetime


def _jinja2_filter_json(json_string):
    tmp = ""
    try:
        tmp = json.loads(json_string)
        tmp = json.dumps(tmp, indent=4)
        tmp = tmp.replace('\n', '<br>')
        tmp = tmp.replace(' ', "&nbsp;")
    except TypeError:
        pass
    return tmp


def _jinja2_filter_json_to_list(json_string):
    out = []
    try:
        paths = []
        tmp = json.loads(json_string)
        for item in tmp:
            if not item['filepath'] in paths:
                out.append(item)
                paths.append(item['filepath'])
    except TypeError:
        pass
    return out


def _jinja2_filter_strip_file(path_string):
    tmp = ""
    try:
        tmp = "/".join(path_string.split("/")[1::])
    except TypeError:
        pass
    return tmp


def _jinja2_filter_convert_timestamp(unix_string):
    tmp = ""
    try:
        timestamp = int(unix_string.strip('"'))
        tmp = datetime.datetime.fromtimestamp(
        timestamp
    ).strftime('<nobr>%Y-%m-%d</nobr> <nobr>%H:%M:%S</nobr>')

    except (TypeError, AttributeError) as e:
        pass
    return tmp



class MyModelView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = app.config['RESULTS_PER_PAGE']
    list_template = "admin/custom_list_template.html"
    column_exclude_list = []

    column_formatters = dict(
        title=macro('render_title'),
        _id=macro('render_json'),
        revisions=macro('render_json'),
        files=macro('render_attachments'),
        audio=macro('render_attachments'),
        minutes=macro('render_html'),
        meeting_date=macro('render_date'),
        start_date=macro('render_date'),
        effective_date=macro('render_date'),
        breefing_date=macro('render_date'),
        )
    column_searchable_list = ['title', 'terms',]


admin = Admin(app=app, name='PMG DATA', url='/admin', base_template='admin/my_master.html')

model_names = model_dict.keys()
model_names.sort()

for name in model_names:
    admin.add_view(MyModelView(model_dict[name], db.session, name=name.title(), endpoint=name))

# add our function to the filters of the jinja2 environment
app.jinja_env.filters['json'] = _jinja2_filter_json
app.jinja_env.filters['json_to_list'] = _jinja2_filter_json_to_list
app.jinja_env.filters['strip_file'] = _jinja2_filter_strip_file
app.jinja_env.filters['convert_timestamp'] = _jinja2_filter_convert_timestamp

