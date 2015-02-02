from flask.ext.admin.form import RenderTemplateWidget

from wtforms import widgets, fields
from wtforms.widgets.core import html_params, HTMLString
from wtforms.compat import text_type
from cgi import escape

class CheckboxSelectWidget(widgets.Select):
    """ Select widget that is a list of checkboxes
    """

    def __call__(self, field, **kwargs):
        if 'id' in kwargs:
            del kwargs['id']
        kwargs['class'] = ''
        kwargs['name'] = field.name

        html = ['<div class="form-inline">']
        for val, label, selected in field.iter_choices():
            html.append(self.render_option(val, label, selected, **kwargs))
        html.append('</div>')
        return HTMLString(''.join(html))

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        options = dict(kwargs, value=value)
        options['type'] = 'checkbox'
        if selected:
            options['checked'] = True
        return HTMLString('<div class="checkbox"><label><input %s> %s</label></div>' % (html_params(**options), escape(text_type(label))))


# This widget uses custom template for inline field list
class InlineMembershipsWidget(RenderTemplateWidget):

    def __init__(self):
        super(
            InlineMembershipsWidget,
            self).__init__('admin/inline_membership.html')


# This widget uses custom template for inline field list
class InlineContentWidget(RenderTemplateWidget):

    def __init__(self):
        super(InlineContentWidget, self).__init__('admin/inline_content.html')


# Define wtforms widget and field
class CKTextAreaWidget(widgets.TextArea):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(fields.TextAreaField):
    widget = CKTextAreaWidget()


# This widget uses custom template for inline field list
class InlineFileWidget(RenderTemplateWidget):

    def __init__(self):
        super(InlineFileWidget, self).__init__('admin/inline_file.html')
