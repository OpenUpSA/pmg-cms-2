from flask_admin.form import RenderTemplateWidget

from wtforms import widgets, fields
from wtforms.widgets.core import html_params, HTMLString
from wtforms.compat import text_type
import html


class CheckboxSelectWidget(widgets.Select):
    """ Select widget that is a list of checkboxes
    """

    def __call__(self, field, **kwargs):
        if "id" in kwargs:
            del kwargs["id"]
        kwargs["class"] = ""
        kwargs["name"] = field.name

        html = ['<div class="form-inline">']
        for val, label, selected in field.iter_choices():
            html.append(self.render_option(val, label, selected, **kwargs))
        html.append("</div>")
        return HTMLString("".join(html))

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        options = dict(kwargs, value=value)
        options["type"] = "checkbox"
        if selected:
            options["checked"] = True
        return HTMLString(
            '<div class="checkbox"><label><input %s> %s</label></div>'
            % (html_params(**options), html.escape(text_type(label)))
        )


# This widget uses custom template for inline field list
class InlineMembershipsWidget(RenderTemplateWidget):
    def __init__(self):
        super(InlineMembershipsWidget, self).__init__("admin/inline_membership.html")


# This widget uses custom template for event files
class InlineFileWidget(RenderTemplateWidget):
    def __init__(self):
        super(InlineFileWidget, self).__init__("admin/inline_file.html")


# Custom widget for showing inline events for bills
class InlineBillEventsWidget(RenderTemplateWidget):
    def __init__(self):
        super(InlineBillEventsWidget, self).__init__("admin/inline_bill_events.html")

    def is_committee_meeting(self, event):
        """ This hides inline deletion and other editing for committee meeting events. """
        return not (event.object_data and event.object_data.type == "committee-meeting")

    def __call__(self, field, **kwargs):
        kwargs["check"] = self.is_committee_meeting
        return super(InlineBillEventsWidget, self).__call__(field, **kwargs)
