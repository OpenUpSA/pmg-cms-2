from builtins import str

import logging
from operator import itemgetter
import datetime
from dateutil.relativedelta import relativedelta

from flask import flash, redirect, url_for, request, make_response
from flask_admin import Admin, expose, BaseView, AdminIndexView
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.ajax import QueryAjaxModelLoader, DEFAULT_PAGE_SIZE
from flask_admin.contrib.sqla.fields import InlineModelFormList
from flask_admin.contrib.sqla.filters import BaseSQLAFilter, DateBetweenFilter
from flask_admin.model.form import InlineFormAdmin
from flask_admin.model.template import macro
from flask_admin.form import rules
from flask_admin.helpers import get_url
from flask_security.changeable import change_user_password
from flask_security.confirmable import confirm_user
from flask import jsonify
from wtforms import fields
from wtforms import widgets as wtforms_widgets
from wtforms.validators import data_required
from sqlalchemy import func
from sqlalchemy.sql.expression import or_, and_
from sqlalchemy import exc
from markupsafe import Markup
import humanize
import datetime
import flask_wtf

from pmg import app, db
from pmg.models import *  # noqa
import pmg.utils
from .xlsx import XLSXBuilder
from .email_alerts import EmailAlertView
from .email_alerts import SubscriptionsView
from .rbac import RBACMixin
from .reports import ReportView
from . import widgets

logger = logging.getLogger(__name__)

SAST = datetime.timezone(offset=datetime.timedelta(0), name="SAST")


def strip_filter(value):
    if value is not None and hasattr(value, "strip"):
        return value.strip()
    return value


# Our base form extends flask_wtf.Form to get CSRF support,
# and adds the _obj property required by Flask Admin
class BaseForm(flask_wtf.Form):
    def __init__(self, formdata=None, obj=None, prefix="", **kwargs):
        self._obj = obj
        super(BaseForm, self).__init__(
            formdata=formdata, obj=obj, prefix=prefix, **kwargs
        )

    class Meta:
        def bind_field(self, form, unbound_field, options):
            # ensure that all form fields strip() their values,
            # so that we don't get random whitespace at the end
            # of a field. Why WTForms doesn't do this by default
            # is beyond me.
            if unbound_field.field_class != InlineModelFormList:
                filters = unbound_field.kwargs.get("filters", [])
                filters.append(strip_filter)
                return unbound_field.bind(form=form, filters=filters, **options)
            return unbound_field.bind(form=form, **options)


class MyIndexView(RBACMixin, AdminIndexView):
    required_roles = ["editor"]

    @expose("/")
    def index(self):

        record_counts = [
            ("Members", "member.index_view", Member.query.count()),
            ("Bill", "bill.index_view", Bill.query.count()),
            ("Committee", "committee.index_view", Committee.query.count()),
            (
                "Committee Meetings",
                "committee-meeting.index_view",
                Event.query.filter_by(type="committee-meeting").count(),
            ),
            ("Questions & Replies", "question.index_view", QuestionReply.query.count()),
            (
                "Calls for Comment",
                "call-for-comment.index_view",
                CallForComment.query.count(),
            ),
            ("Daily Schedules", "schedule.index_view", DailySchedule.query.count()),
            ("Gazette", "gazette.index_view", Gazette.query.count()),
            (
                "Hansards",
                "hansard.index_view",
                Event.query.filter_by(type="plenary").count(),
            ),
            (
                "Media Briefings",
                "briefing.index_view",
                Event.query.filter_by(type="media-briefing").count(),
            ),
            ("Policy Documents", "policy.index_view", PolicyDocument.query.count()),
            (
                "Tabled Committee Reports",
                "tabled-committee-report.index_view",
                TabledCommitteeReport.query.count(),
            ),
            ("Uploaded Files", "files.index_view", File.query.count()),
            ("Search Alerts", "", SavedSearch.query.count()),
        ]
        record_counts = sorted(record_counts, key=itemgetter(2), reverse=True)

        return self.render("admin/my_index.html", record_counts=record_counts)


class UsageReportView(RBACMixin, BaseView):
    required_roles = [
        "editor",
    ]

    def get_list(self, months):
        cutoff = datetime.datetime.utcnow() - relativedelta(months=months)
        organisation_list = (
            db.session.query(
                Organisation.name,
                Organisation.domain,
                db.func.count(User.id).label("num_users"),
            )
            .join(Organisation.users)
            .filter(User.current_login_at > cutoff)
            .group_by(Organisation.id)
            .order_by(Organisation.name)
            .all()
        )
        return organisation_list

    @expose("/")
    @expose("/<int:months>/")
    def index(self, months=1):

        return self.render(
            "admin/usage_report.html",
            org_list=self.get_list(months),
            num_months=months,
            today=datetime.date.today(),
        )

    def xlsx(self, users, filename):
        builder = XLSXBuilder()
        xlsx = builder.from_orgs(users)
        resp = make_response(xlsx)
        resp.headers["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp.headers["Content-Disposition"] = "attachment;filename=" + filename
        return resp

    @expose("/xlsx/<int:months>/")
    def download(self, months=1):
        today = datetime.date.today()
        tmp = str(months) + " month up to " + str(today)
        if months > 1:
            tmp = str(months) + " months up to " + str(today)
        filename = "PMG active organisations - " + tmp + ".xlsx"
        return self.xlsx(self.get_list(months), filename=filename)


class MyModelView(RBACMixin, ModelView):
    form_base_class = BaseForm

    required_roles = ["editor"]

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    export_max_rows = 10000
    export_types = ["csv", "xlsx"]
    edit_template = "admin/my_edit.html"
    create_template = "admin/my_create.html"
    list_template = "admin/my_list.html"

    def frontend_url(self, model):
        if hasattr(model, "url") and model.id is not None:
            return model.url
        return None

    def alert_url(self, model):
        """If we support sending an email alert about this model, what's the URL?"""
        if model.id and hasattr(model, "alert_template"):
            template = model.alert_template
            if template:
                params = {}
                params[model.resource_content_type + "_id"] = model.id
                params["template_id"] = template.id
                params["committee_ids"] = model.committee_id
                params["prefill"] = "1"
                return url_for("alerts.new", **params)

    def _validate_form_instance(self, *args, **kwargs):
        # XXX: hack around rulesets removing CSRF tokens
        # XXX: see https://github.com/flask-admin/flask-admin/issues/1180
        pass

    def get_export_columns(self):
        """Export all columns by default."""
        return self.get_column_names(
            only_columns=self.scaffold_list_columns(),
            excluded_columns=self.column_export_exclude_list,
        )

    # @expose('/admin/<model>/delete', methods=('POST', ))
    # def delete_view(self):
    #     """
    #     Delete the model
    #     """
    #     print('*******************************')
    #     print('DELETING THE MODEL')
    #     id = request.args.get('id')
    #     print(id)
    #     print('***********************************')
    #     if id is None:
    #         return jsonify({"success": False}), 404
    #     model = self.get_one(id)
    #     db.session.delete(model)
    #     db.session.commit()
    #     flash("{0} deleted".format(model))
    #     return jsonify({"success": True}), 200


class HasExpiredFilter(BaseSQLAFilter):
    def __init__(self, column, name):
        options = (
            ("expired", "Expired"),
            ("unexpired", "Not expired"),
            ("1month", "Expiring in 1 month"),
            ("3month", "Expiring in 3 months"),
            ("6month", "Expiring in 6 months"),
            ("1year", "Expiring in 1 year"),
        )
        super(HasExpiredFilter, self).__init__(column, name, options=options)

    def apply(self, query, value):
        if value == "expired":
            return query.filter(self.column < datetime.date.today()).filter(
                self.column != None
            )  # noqa

        elif value == "unexpired":
            return query.filter(
                or_(self.column == None, self.column >= datetime.date.today())  # noqa
            )

        elif value == "1month":
            return query.filter(self.column >= datetime.date.today()).filter(
                self.column <= datetime.date.today() + relativedelta(months=1)
            )

        elif value == "3month":
            return query.filter(self.column >= datetime.date.today()).filter(
                self.column <= datetime.date.today() + relativedelta(months=3)
            )

        elif value == "6month":
            return query.filter(self.column >= datetime.date.today()).filter(
                self.column <= datetime.date.today() + relativedelta(months=6)
            )

        elif value == "1year":
            return query.filter(self.column >= datetime.date.today()).filter(
                self.column <= datetime.date.today() + relativedelta(years=1)
            )

        else:
            return query

    def operation(self):
        return "is"


class UserView(MyModelView):
    required_roles = ["user-admin"]

    can_create = True
    can_delete = True
    column_list = [
        "email",
        "active",
        "created_at",
        "current_login_at",
        "login_count",
        "expiry",
    ]
    column_labels = {
        "current_login_at": "Last seen",
        "subscriptions": "User's premium subscriptions",
    }
    column_export_exclude_list = ["password"]
    form_columns = [
        "email",
        "name",
        "confirmed_at",
        "active",
        "roles",
        "organisation",
        "expiry",
        "subscribe_daily_schedule",
        "subscriptions",
        "committee_alerts",
    ]
    form_args = {
        "subscriptions": {
            "query_factory": Committee.premium_for_select,
            "widget": widgets.CheckboxSelectWidget(multiple=True),
        },
        "confirmed_at": {
            "widget": wtforms_widgets.TextInput(),
        },
    }
    form_widget_args = {
        "confirmed_at": {"readonly": True},
    }
    column_labels = {
        "confirmed_at": "Email address confirmed at",
    }
    column_default_sort = (User.created_at, True)
    column_formatters = {"current_login_at": macro("datetime_as_date")}
    column_formatters_export = {}
    column_searchable_list = ("email",)
    column_filters = [
        HasExpiredFilter(User.expiry, "Subscription expiry"),
        DateBetweenFilter(User.expiry, "Expiry date"),
    ]

    def on_model_change(self, form, model, is_created):
        # ensure that organisation is set automatically
        model.email = model.email
        if model.organisation:
            model.expiry = model.organisation.expiry

    @expose("/reset_password", methods=["GET", "POST"])
    def reset_user_password(self):
        user = User.query.get(request.args["model_id"])
        new_pwd = request.form["new_password"]
        return_url = request.headers["Referer"]

        if user is None:
            flash(gettext("User not found. Please try again."), "error")
            return redirect(return_url)

        if len(new_pwd) < 6:
            flash(
                gettext(
                    "A password must contain at least 6 characters. Please try again."
                ),
                "error",
            )
            return redirect(return_url)

        if " " in new_pwd:
            flash(
                gettext("Passwords cannot contain spaces. Please try again."), "error"
            )
            return redirect(return_url)

        change_user_password(user, new_pwd)
        db.session.commit()

        flash(
            gettext(
                "The password has been changed successfully. A notification has been sent to %s."
                % user.email
            )
        )
        return redirect(return_url)

    @expose("/confirm", methods=["GET", "POST"])
    def confirm_user(self):
        user = User.query.get(request.args["model_id"])
        return_url = request.headers["Referer"]

        if user is None:
            flash(gettext("User not found. Please try again."), "error")
            return redirect(return_url)

        confirm_user(user)
        db.session.commit()

        flash(
            gettext(
                "The user's email address %s has been confirmed. They will now received emails."
                % user.email
            )
        )
        return redirect(return_url)


class OrganisationView(MyModelView):
    can_create = True

    column_list = [
        "name",
        "domain",
        "paid_subscriber",
        "expiry",
    ]
    column_searchable_list = ("domain", "name")
    column_filters = [
        HasExpiredFilter(Organisation.expiry, "Subscription expiry"),
        DateBetweenFilter(Organisation.expiry, "Expiry date"),
    ]
    form_ajax_refs = {
        "users": {"fields": ("name", "email"), "page_size": 25},
    }
    form_columns = [
        "name",
        "domain",
        "contact",
        "paid_subscriber",
        "expiry",
        "subscriptions",
        "users",
    ]
    form_args = {
        "subscriptions": {
            "query_factory": Committee.premium_for_select,
            "widget": widgets.CheckboxSelectWidget(multiple=True),
        }
    }
    column_labels = {"subscriptions": "Premium subscriptions"}


class CommitteeView(MyModelView):

    can_delete = True
    column_list = ("name", "house", "ad_hoc", "memberships")
    column_labels = {
        "memberships": "Members",
        "minister": "Associated Minister",
    }
    column_sortable_list = (
        "name",
        ("house", "house.name"),
        "ad_hoc",
    )
    column_default_sort = (Committee.name, False)
    column_searchable_list = ("name",)
    column_formatters = dict(
        memberships=macro("render_membership_count"),
    )
    form_columns = (
        "name",
        "ad_hoc",
        "active",
        "premium",
        "monitored",
        "house",
        "minister",
        "about",
        "contact_details",
        "memberships",
    )
    form_widget_args = {
        "about": {"class": "pmg_ckeditor"},
        "contact_details": {"class": "pmg_ckeditor"},
    }
    form_args = {
        "memberships": {"widget": widgets.InlineMembershipsWidget()},
    }

    inline_models = (Membership,)

    @expose("/delete", methods=["DELETE"])
    def delete_view(self):
        """
        Delete the model
        """
        id = request.args.get("id")
        if id is None:
            return jsonify({"success": False}), 404
        model = self.get_one(id)
        try:
            db.session.delete(model)
            db.session.commit()
            flash("{0} deleted".format(model.name))
            return jsonify({"success": "ok"}), 200
        except exc.IntegrityError as error:
            reason = "unable to delete model: {}".format(error)
            return jsonify({"success": False, "reason": reason})


class ViewWithFiles:
    """Mixin to pre-fill inline file forms."""

    form_args = {
        "files": {"widget": widgets.InlineFileWidget()},
    }

    def on_form_prefill(self, form, id):
        if hasattr(form, "files"):
            for f in form.files:
                f.title.data = f.object_data.file.title


class InlineFile(InlineFormAdmin):
    """Inline file admin for all views that allow file attachments.
    It allows the user to choose an existing file to link as
    an attachment, or upload a new one. It also allows the user
    to edit the title of an already-attached file.
    """

    form_columns = (
        "id",
        "file",
    )
    column_labels = {
        "file": "Existing file",
    }
    form_ajax_refs = {
        "file": {
            "fields": ("title", "file_path"),
            "page_size": 10,
        }
    }

    def postprocess_form(self, form_class):
        # add a field for handling the file upload
        form_class.upload = fields.FileField("Upload a file")
        form_class.file.kwargs["validators"] = []
        form_class.file.kwargs["allow_blank"] = True
        form_class.title = fields.TextField("Title")
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

    form_excluded_columns = ("type",)
    column_exclude_list = ("type",)
    column_formatters = {"date": lambda v, c, model, n: model.date.astimezone(SAST)}

    def on_form_prefill(self, form, id):
        super().on_form_prefill(form, id)
        # Display date in South African time
        form.date.data = form.date.object_data.astimezone(SAST)

    def __init__(self, model, session, **kwargs):
        self.type = kwargs.pop("type")
        super(EventView, self).__init__(model, session, **kwargs)

    def on_model_change(self, form, model, is_created):
        if is_created:
            # set some default values when creating a new record
            model.type = self.type
        # make sure the new date is timezone aware
        if model.date:
            model.date = model.date.replace(tzinfo=SAST)

        model.autolink_bills()

    def get_query(self):
        """
        Add filter to return only records of the specified type.
        """

        return self.session.query(self.model).filter(self.model.type == self.type)

    def get_count_query(self):
        """
        Add filter to return only records of the specified type.
        """

        return (
            self.session.query(func.count("*"))
            .select_from(self.model)
            .filter(self.model.type == self.type)
        )


class AttendanceMemberAjaxModelLoader(QueryAjaxModelLoader):
    def format(self, model):
        if not model:
            return None

        if model.house:
            model_unicode = "%s (%s)" % (model.name, model.house.name)
        else:
            model_unicode = "%s" % model.name
        return (getattr(model, self.pk), model_unicode)

    def get_list(self, term, offset=0, limit=DEFAULT_PAGE_SIZE):
        query = self.session.query(self.model)
        # Only show currently active members
        query = query.filter(Member.current == True)

        filters = (field.ilike("%%%s%%" % term) for field in self._cached_fields)
        query = query.filter(or_(*filters))

        if self.order_by:
            query = query.order_by(self.order_by)

        return query.offset(offset).limit(limit).all()


class InlineCommitteeMeetingAttendance(InlineFormAdmin):
    form_columns = (
        "id",
        "member",
        "attendance",
        "chairperson",
        "alternate_member",
    )
    form_ajax_refs = {
        "member": AttendanceMemberAjaxModelLoader(
            "committeemeetingattendance-member",
            db.session,
            Member,
            fields=["name"],
            limit=25,
        ),
    }
    form_choices = {
        "attendance": [
            ("A", "A - Absent"),
            ("AP", "AP - Absent with Apologies"),
            ("DE", "DE - Departed Early"),
            ("L", "AL - Arrived Late"),
            ("LDE", "LDE - Arrived Late and Departed Early"),
            ("P", "P - Present"),
            ("U", "U - Unknown"),
        ]
    }


class CommitteeMeetingView(EventView):
    column_list = ("date", "title", "committee", "featured")
    column_labels = {
        "committee": "Committee",
    }
    column_sortable_list = (
        "date",
        ("committee", "committee.name"),
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ("committee.name", "title")
    column_filters = ["committee.name", "date"]
    column_export_exclude_list = ["summary", "body"]
    form_edit_rules = (
        "committee",
        "title",
        "date",
        "chairperson",
        "featured",
        "public_participation",
        "bills",
        "summary",
        "body",
        "files",
        rules.FieldSet(
            ["actual_start_time", "actual_end_time", "attendance"],
            "Member Attendance Record",
        ),
    )
    form_create_rules = form_edit_rules
    form_args = {
        "summary": {"default": "<p>Report of the meeting to follow.</p>"},
        "committee": {"validators": [data_required()]},
        "files": {"widget": widgets.InlineFileWidget()},
    }
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
        "summary": {"class": "pmg_ckeditor"},
    }
    form_ajax_refs = {"bills": {"fields": ("title",), "page_size": 50}}
    inline_models = [
        InlineFile(EventFile),
        InlineCommitteeMeetingAttendance(CommitteeMeetingAttendance),
    ]

    def on_model_change(self, form, model, is_created):
        super(CommitteeMeetingView, self).on_model_change(form, model, is_created)
        # make sure the new times are timezone aware
        for attr in ["actual_start_time", "actual_end_time"]:
            if getattr(model, attr):
                setattr(model, attr, getattr(model, attr).replace(tzinfo=SAST))


class HansardView(EventView):
    column_list = (
        "house",
        "title",
        "date",
    )
    column_sortable_list = (
        "title",
        "house",
        "date",
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ("title",)
    form_columns = (
        "date",
        "house",
        "title",
        "bills",
        "body",
        "files",
    )
    form_args = {
        "house": {"validators": [data_required()]},
    }
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }
    form_ajax_refs = {"bills": {"fields": ("title",), "page_size": 50}}
    inline_models = [InlineFile(EventFile)]


class ProvincialLegislatureView(MyModelView):
    can_delete = False
    can_create = False

    column_list = ("name",)
    column_sortable_list = ("name",)
    form_columns = (
        "name",
        "contact_details",
        "speaker",
    )
    form_widget_args = {
        "contact_details": {"class": "pmg_ckeditor"},
        "name": {"readonly": True},
        "speaker": {"fields": ("name",), "page_size": 25},
    }

    def frontend_url(self, model):
        if model.id:
            return url_for(
                "provincial_legislatures_detail",
                slug=pmg.utils.slugify_province(model.name),
            )
        return None

    def get_query(self):
        """
        Add filter to return only provincial legislatures
        """

        return self.session.query(self.model).filter(self.model.sphere == "provincial")


class BriefingView(EventView):
    column_list = (
        "title",
        "date",
        "committee",
    )
    column_sortable_list = (
        "title",
        "date",
    )
    column_default_sort = (Event.date, True)
    column_searchable_list = ("title",)
    form_columns = (
        "title",
        "date",
        "committee",
        "summary",
        "body",
        "files",
    )
    form_widget_args = {
        "summary": {"class": "pmg_ckeditor"},
        "body": {"class": "pmg_ckeditor"},
    }
    inline_models = [InlineFile(EventFile)]


class MemberView(MyModelView):
    column_list = (
        "name",
        "house",
        "party",
        "province",
        "memberships",
        "current",
        "pa_link",
        "profile_pic_url",
    )
    column_labels = {
        "memberships": "Committees",
        "current": "Currently active",
        "pa_link": "PA Link",
    }
    column_sortable_list = (
        "name",
        ("house", "house.name"),
        ("party", "party.name"),
        ("province", "province.name"),
        "bio",
        "profile_pic_url",
    )
    column_default_sort = (Member.name, False)
    column_searchable_list = ("name",)
    column_formatters = dict(
        profile_pic_url=macro("render_profile_pic"),
        memberships=macro("render_committee_membership"),
        pa_link=macro("render_external_link"),
    )
    column_formatters_export = {}
    column_filters = ["current", "house.name", "party.name", "province.name"]
    form_columns = (
        "name",
        "current",
        "house",
        "party",
        "province",
        "bio",
        "pa_link",
        "upload",
    )
    form_extra_fields = {"upload": fields.FileField("Profile pic")}
    form_overrides = dict(bio=fields.TextAreaField)
    form_ajax_refs = {"events": {"fields": ("date", "title", "type"), "page_size": 25}}
    form_widget_args = {
        "bio": {"rows": "10"},
    }
    edit_template = "admin/edit_member.html"

    def on_model_change(self, form, model, is_created):
        # save profile pic, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            tmp = File()
            tmp.from_upload(file_data)
            model.profile_pic_url = tmp.file_path

    @expose("/attendance/")
    def attendance(self):
        """ """
        mem_id = request.args.get("id")
        url = "/admin/committeemeetingattendance/?member_id={0}".format(mem_id)
        return redirect(url)


class CommitteeMeetingAttendanceView(MyModelView):
    can_delete = False
    can_edit = False

    column_list = (
        "meeting.committee.name",
        "meeting.date",
        "meeting.title",
        "attendance",
        "alternate_member",
        "member.name",
    )
    column_labels = {
        "meeting.date": "Meeting date",
        "meeting.title": "Meeting title",
        "meeting.committee.name": "Committee name",
        "attendance": "Attendance code",
        "member.name": "Member",
    }
    column_searchable_list = ("member.name",)
    column_filters = [
        "meeting.date",
        "attendance",
        "alternate_member",
        "meeting.committee",
    ]
    column_formatters = {
        "meeting.title": lambda v, c, m, n: Markup(
            "<a href='%s'>%s</a>"
            % (
                url_for("committee_meeting", event_id=m.meeting_id),
                m.meeting.title,
            ),
        ),
        "meeting.date": lambda v, c, m, n: m.meeting.date.date().isoformat(),
    }

    def get_query(self):
        return self._extend_query(
            super(CommitteeMeetingAttendanceView, self).get_query()
        )

    def get_count_query(self):
        return self._extend_count_query(
            super(CommitteeMeetingAttendanceView, self).get_count_query()
        )

    def _extend_query(self, query):
        member_id = request.args.get("member_id")
        query = query.join(CommitteeMeeting).order_by(CommitteeMeeting.date.desc())
        if member_id is None:
            return query
        return query.filter(CommitteeMeetingAttendance.member_id == member_id)

    def _extend_count_query(self, query):
        member_id = request.args.get("member_id")
        if member_id is None:
            return query
        return query.filter(CommitteeMeetingAttendance.member_id == member_id)


class CommitteeQuestionView(MyModelView):
    list_template = "admin/committee_question_list.html"
    create_template = "admin/committee_question_create.html"

    column_list = (
        "code",
        "minister",
        "question_number",
        "date",
    )
    column_default_sort = ("date", True)
    column_searchable_list = ("code",)
    form_columns = (
        "code",
        "date",
        "intro",
        "question",
        "asked_by_name",
        "asked_by_member",
        "question_to_name",
        "minister",
        "answer",
        "source_file",
        "written_number",
        "oral_number",
        "president_number",
        "deputy_president_number",
    )
    column_labels = {
        "question_to_name": "Question To",
        "minister": "Question To Minister",
    }
    form_args = {
        "files": {"widget": widgets.InlineFileWidget()},
        "minister": {"validators": [data_required()]},
    }
    form_widget_args = {
        "answer": {"class": "pmg_ckeditor"},
    }
    form_ajax_refs = {
        "source_file": {
            "fields": ("title", "file_path"),
            "page_size": 10,
        },
        "asked_by_member": {"fields": ("name",), "page_size": 25},
    }
    inline_models = [InlineFile(CommitteeQuestionFile)]

    @expose("/upload", methods=["POST"])
    def upload(self):
        return_url = request.headers["Referer"]
        file_data = request.files.get("file")
        try:
            question = CommitteeQuestion.import_from_uploaded_answer_file(file_data)
            if question.id:
                # it already existed
                flash("That question has already been imported.", "warn")
                return redirect(get_url(".edit_view", id=question.id, url=return_url))

            db.session.add(question)
            db.session.commit()
            flash("Successfully imported from %s" % (file_data.filename,))
            return redirect(get_url(".edit_view", id=question.id, url=return_url))
        except ValueError as e:
            flash("Couldn't import from %s: %s" % (file_data.filename, e), "error")
            return redirect(return_url)

    def frontend_url(self, model):
        if model.id:
            return url_for("committee_question", question_id=model.id)
        return None


class QuestionReplyView(MyModelView):
    column_list = (
        "minister",
        "title",
        "start_date",
        "question_number",
    )
    column_default_sort = ("start_date", True)
    column_searchable_list = ("title", "question_number")
    form_columns = (
        "minister",
        "title",
        "start_date",
        "question_number",
        "body",
    )
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }
    inline_models = [InlineFile(QuestionReplyFile)]
    column_labels = {
        "minister": "Question To Minister",
    }
    form_args = {
        "minister": {"validators": [data_required()]},
    }


class CallForCommentView(MyModelView):
    column_list = (
        "committee",
        "title",
        "start_date",
        "end_date",
    )
    column_default_sort = ("start_date", True)
    column_searchable_list = ("title",)
    form_columns = (
        "committee",
        "title",
        "start_date",
        "end_date",
        "body",
    )
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }


class DailyScheduleView(ViewWithFiles, MyModelView):
    column_list = (
        "title",
        "start_date",
        "house",
    )
    column_default_sort = ("start_date", True)
    column_searchable_list = ("title",)
    form_columns = (
        "title",
        "start_date",
        "house",
        "body",
        "files",
    )
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }
    inline_models = [InlineFile(DailyScheduleFile)]


class GazetteView(ViewWithFiles, MyModelView):
    column_list = ("title", "effective_date", "start_date")
    column_default_sort = ("effective_date", True)
    column_searchable_list = ("title",)
    form_columns = ("title", "effective_date", "start_date", "files")
    inline_models = [InlineFile(GazetteFile)]


class PoliticalPartyView(ViewWithFiles, MyModelView):
    column_list = ("name",)


class PolicyDocumentView(ViewWithFiles, MyModelView):
    column_list = ("title", "effective_date", "start_date")
    column_default_sort = ("effective_date", True)
    column_searchable_list = ("title",)
    form_columns = ("title", "effective_date", "start_date", "files")
    inline_models = [InlineFile(PolicyDocumentFile)]


class TabledCommitteeReportView(ViewWithFiles, MyModelView):
    column_list = (
        "committee",
        "title",
        "start_date",
    )
    column_default_sort = ("start_date", True)
    column_searchable_list = ("title",)
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }
    form_columns = (
        "committee",
        "title",
        "start_date",
        "body",
        "files",
    )
    inline_models = [InlineFile(TabledCommitteeReportFile)]


class EmailTemplateView(MyModelView):
    column_list = (
        "name",
        "subject",
        "description",
    )
    column_default_sort = ("name", True)
    column_searchable_list = ("name", "subject", "description", "body")
    form_columns = (
        "name",
        "description",
        "subject",
        "body",
    )
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
    }


class EventTypeSelectField(fields.SelectField):
    def condition(self):
        if self.data == "plenary":
            return True
        return False

    def __call__(self, *args, **kwargs):
        if self.condition():
            kwargs.setdefault("readonly", True)
        return super(EventTypeSelectField, self).__call__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(EventTypeSelectField, self).__init__(*args, **kwargs)

        self.choices = [
            ("plenary", "Hansard"),
            ("bill-introduced", "Bill introduced"),
            ("bill-updated", "Bill updated"),
            ("bill-passed", "Bill passed"),
            ("bill-signed", "Bill signed"),
            ("bill-enacted", "Bill enacted"),
            ("bill-act-commenced", "Act commenced"),
        ]

    def populate_obj(self, obj, name):
        """
        If a type is already on hansard and is changes we resave it as hansard
        """
        if obj.type == "plenary" and self.data != "plenary":
            self.data = "plenary"
            super(EventTypeSelectField, self).populate_obj(obj, name)
        else:
            super(EventTypeSelectField, self).populate_obj(obj, name)


class InlineBillEventsForm(InlineFormAdmin):
    ALLOWED_BILL_PASSED_TITLES = [
        "Bill passed by the National Assembly and transmitted to the NCOP for concurrence",
        "Bill passed by both Houses and sent to President for assent",
        "Bill passed by the NCOP and returned to the National Assembly for concurrence",
        "Bill passed and amended by the NCOP and returned to the National Assembly for concurrence",
        "Bill passed by the NCOP and sent to the President for assent",
        "The NCOP rescinded its decision",
        "Bill remitted",
        "Bill revived on this date",
    ]
    ALLOWED_BILL_UPDATED_TITLES = [
        "The NA rescinded its decision to pass Bill",
        "Bill rejected",
        "The NA granted permission",
        "The NCOP granted permission",
        "Bill lapsed",
        "Bill withdrawn",
    ]
    form_columns = (
        "id",
        "date",
        "type",
        "title",
        "house",
        "member",
    )
    form_overrides = {"type": EventTypeSelectField}
    form_args = {
        "title": {
            "description": '<div><a href="#" class="help-event-title">'
            '<i class="fa fa-icon fa-fw fa-chevron-right"></i>Help?</a>'
            '<div class="help-event-title-content">When event type is "Bill passed", '
            'event title must be one of: <ul>%s</ul>When event type is "Bill updated", '
            "event title must be one of: <ul>%s</ul></div></div>"
            % (
                "".join(
                    ("<li>%s</li>" % title for title in ALLOWED_BILL_PASSED_TITLES)
                ),
                "".join(
                    ("<li>%s</li>" % title for title in ALLOWED_BILL_UPDATED_TITLES)
                ),
            )
        },
    }

    form_ajax_refs = {
        "member": {"fields": ("name",), "page_size": 25},
    }

    def on_model_change(self, form, model):
        # make sure the new date is timezone aware
        model.date = model.date.replace(tzinfo=SAST)


class InlineBillVersionForm(InlineFormAdmin):
    form_columns = (
        "id",
        "date",
        "title",
        "enacted",
        "file",
    )
    column_labels = {"enacted": "As enacted?"}
    form_ajax_refs = {"file": {"fields": ("title", "file_path"), "page_size": 25}}

    def postprocess_form(self, form_class):
        # TODO: hide this for existing versions
        form_class.upload = fields.FileField("Upload a new file")
        return form_class

    def on_model_change(self, form, model):
        # save file, if it is present
        file_data = request.files.get(form.upload.name)
        if file_data:
            if not model.file:
                model.file = File()

            model.file.from_upload(file_data)


class BillHouseAjaxModelLoader(QueryAjaxModelLoader):
    def get_list(self, term, offset=0, limit=DEFAULT_PAGE_SIZE):
        query = self.session.query(self.model)

        filters = list((field.ilike("%%%s%%" % term) for field in self._cached_fields))
        query = query.filter(or_(*filters))
        query = query.filter(and_(House.sphere == "national"))

        if self.order_by:
            query = query.order_by(self.order_by)

        return query.offset(offset).limit(limit).all()


class BillsView(MyModelView):
    column_list = (
        "code",
        "title",
        "type.name",
        "status.name",
    )
    column_labels = {
        "type.name": "Type",
        "status.name": "Status",
    }
    form_ajax_refs = {
        "place_of_introduction": BillHouseAjaxModelLoader(
            "place_of_introduction", db.session, House, fields=["name", "name_short"]
        ),
    }
    form_columns = (
        "year",
        "number",
        "title",
        "type",
        "introduced_by",
        "date_of_introduction",
        "place_of_introduction",
        "status",
        "date_of_assent",
        "effective_date",
        "act_name",
        "versions",
    )
    column_default_sort = ("year", True)
    column_searchable_list = ("title",)
    inline_models = [
        InlineBillEventsForm(Event),
        InlineBillVersionForm(BillVersion),
    ]
    form_args = {
        "events": {"widget": widgets.InlineBillEventsWidget()},
    }


class MinisterView(MyModelView):
    column_list = ("name",)
    column_default_sort = ("name", True)
    column_searchable_list = ("name",)
    form_columns = ("name",)


class FeaturedContentView(MyModelView):
    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        model.start_date = model.start_date.replace(tzinfo=SAST)


class FileView(MyModelView):
    column_list = ("title", "file_path", "file_bytes")
    column_searchable_list = ("title", "file_path")
    column_default_sort = "file_path"
    column_labels = {"file_bytes": "Size"}
    column_formatters = {
        "file_bytes": lambda v, c, m, n: (
            "-"
            if m.file_bytes is None
            else Markup("<nobr>%s</nobr>" % humanize.naturalsize(m.file_bytes))
        ),
    }

    class SizeRule(rules.BaseRule):
        def __call__(self, form, form_opts=None, field_args={}):
            if form._obj.file_bytes:
                return humanize.naturalsize(form._obj.file_bytes)
            return "-"

    class UrlRule(rules.BaseRule):
        def __call__(self, form, form_opts=None, field_args={}):
            url = url_for("docs", path=form.file_path.data)
            return Markup('<a href="%s" target="_blank">%s</a>' % (url, url))

    form_columns = (
        "title",
        "description",
        "file_path",
        "file_mime",
        "file_bytes",
    )
    form_widget_args = {
        "file_mime": {"readonly": True},
        "file_path": {"readonly": True},
        "file_bytes": {"readonly": True},
    }

    form_edit_rules = [
        "title",
        "description",
        "file_path",
        "file_mime",
        "file_bytes",
        rules.Container("rules.staticfield", SizeRule(), label="Size"),
        rules.Container("rules.staticfield", UrlRule(), label="URL"),
    ]

    form_create_rules = ["title", "description", "upload"]

    def get_create_form(self):
        # allow user to upload a file when creating form
        form = super(FileView, self).get_create_form()
        form.upload = fields.FileField("Upload a file", [data_required()])
        return form

    def on_model_change(self, form, model, is_create):
        if is_create:
            file_data = request.files.get(form.upload.name)
            model.from_upload(file_data)


class RedirectView(MyModelView):
    column_list = ("old_url", "new_url", "nid")
    column_searchable_list = ("old_url", "new_url")
    column_default_sort = "old_url"


class BillStatusView(MyModelView):
    column_default_sort = "name"
    column_list = ("name", "description")
    form_columns = column_list
    edit_modal = True
    create_modal = True


class PageView(ViewWithFiles, MyModelView):
    column_list = ("slug", "title", "featured", "date")
    column_searchable_list = ("slug", "title")
    column_default_sort = "slug"

    form_columns = (
        "title",
        "slug",
        "path",
        "body",
        "featured",
        "date",
        "show_files",
        "files",
    )
    form_extra_fields = {
        "path": fields.TextField("Path"),
    }
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
        "path": {"readonly": True},
    }
    inline_models = [InlineFile(PageFile)]
    column_descriptions = {
        "show_files": "Show a list of the files attached to this page in a box on the right?",
    }

    def frontend_url(self, model):
        return "/page/%s" % model.slug

    def on_form_prefill(self, form, id):
        super(PageView, self).on_form_prefill(form, id)
        form.path.data = "/page/%s" % form.slug.data

    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        if model.date:
            model.date = model.date.replace(tzinfo=SAST)


class PostView(ViewWithFiles, MyModelView):
    column_list = ("slug", "title", "date")
    column_searchable_list = ("slug", "title")
    column_default_sort = "slug"

    form_columns = ("title", "slug", "path", "body", "featured", "date", "files")
    form_extra_fields = {
        "path": fields.TextField("Path"),
    }
    form_widget_args = {
        "body": {"class": "pmg_ckeditor"},
        "path": {"readonly": True},
    }
    form_args = {
        "date": {"default": datetime.datetime.now()},
    }
    inline_models = [InlineFile(PostFile)]
    column_descriptions = {
        "show_files": "Show a list of the files attached to this page in a box on the right?",
    }

    def frontend_url(self, model):
        return "/blog/%s" % model.slug

    def on_form_prefill(self, form, id):
        super(PostView, self).on_form_prefill(form, id)
        form.path.data = "/blog/%s" % form.slug.data

    def on_model_change(self, form, model, is_created):
        # make sure the new date is timezone aware
        if model.date:
            model.date = model.date.replace(tzinfo=SAST)


# initialise admin instance
admin = Admin(
    app,
    name="PMG-CMS",
    base_template="admin/my_base.html",
    index_view=MyIndexView(name="Home"),
    template_mode="bootstrap3",
)

# ---------------------------------------------------------------------------------
# Users
admin.add_view(
    UserView(User, db.session, name="Users", endpoint="user", category="Users")
)
admin.add_view(
    OrganisationView(
        Organisation,
        db.session,
        name="Organisations",
        endpoint="organisation",
        category="Users",
    )
)

# ---------------------------------------------------------------------------------
# Committees
admin.add_view(
    CommitteeView(
        Committee,
        db.session,
        name="Committees",
        endpoint="committee",
        category="Committees",
    )
)
admin.add_view(
    CommitteeMeetingView(
        CommitteeMeeting,
        db.session,
        type="committee-meeting",
        name="Committee Meetings",
        endpoint="committee-meeting",
        category="Committees",
    )
)
admin.add_view(
    CallForCommentView(
        CallForComment,
        db.session,
        name="Calls for Comment",
        endpoint="call-for-comment",
        category="Committees",
    )
)
admin.add_view(
    CommitteeQuestionView(
        CommitteeQuestion,
        db.session,
        name="Questions to Committees",
        endpoint="committee-question",
        category="Committees",
    )
)
admin.add_view(
    MinisterView(
        Minister,
        db.session,
        name="Ministers",
        endpoint="minister",
        category="Committees",
    )
)
admin.add_view(
    QuestionReplyView(
        QuestionReply,
        db.session,
        name="Old Questions & Replies",
        endpoint="question",
        category="Committees",
    )
)
admin.add_view(
    TabledCommitteeReportView(
        TabledCommitteeReport,
        db.session,
        name="Tabled Committee Reports",
        endpoint="tabled-committee-report",
        category="Committees",
    )
)

# ---------------------------------------------------------------------------------
# Bills
admin.add_view(BillsView(Bill, db.session, name="Bills", endpoint="bill"))

# ---------------------------------------------------------------------------------
# Other Content
admin.add_view(
    DailyScheduleView(
        DailySchedule,
        db.session,
        name="Daily Schedules",
        endpoint="schedule",
        category="Other Content",
    )
)
admin.add_view(
    FeaturedContentView(
        Featured,
        db.session,
        name="Featured Content",
        endpoint="featured",
        category="Other Content",
    )
)
admin.add_view(
    GazetteView(
        Gazette,
        db.session,
        name="Gazettes",
        endpoint="gazette",
        category="Other Content",
    )
)
admin.add_view(
    HansardView(
        Hansard,
        db.session,
        type="plenary",
        name="Hansards",
        endpoint="hansard",
        category="Other Content",
    )
)
admin.add_view(
    PoliticalPartyView(
        Party,
        db.session,
        name="Political Parties",
        endpoint="party",
        category="Other Content",
    )
)
admin.add_view(
    ProvincialLegislatureView(
        House,
        db.session,
        name="Provincial Legislatures",
        endpoint="provincial-legislatures",
        category="Other Content",
    )
)
admin.add_view(
    BriefingView(
        Briefing,
        db.session,
        type="media-briefing",
        name="Media Briefings",
        endpoint="briefing",
        category="Other Content",
    )
)
admin.add_view(
    RedirectView(
        Redirect,
        db.session,
        category="Other Content",
        name="Legacy Redirects",
        endpoint="redirects",
    )
)
admin.add_view(
    PolicyDocumentView(
        PolicyDocument,
        db.session,
        name="Policy Document",
        endpoint="policy",
        category="Other Content",
    )
)
admin.add_view(
    PageView(
        Page,
        db.session,
        category="Other Content",
        name="Static Pages",
        endpoint="pages",
    )
)
admin.add_view(
    PostView(
        Post, db.session, category="Other Content", name="Blog Posts", endpoint="posts"
    )
)
admin.add_view(
    FileView(
        File,
        db.session,
        category="Other Content",
        name="Uploaded Files",
        endpoint="files",
    )
)

# ---------------------------------------------------------------------------------
# Email alerts
admin.add_view(
    EmailAlertView(category="Email Alerts", name="Send Emails", endpoint="alerts")
)
admin.add_view(
    EmailTemplateView(
        EmailTemplate,
        db.session,
        name="Email Templates",
        category="Email Alerts",
        endpoint="email-templates",
    )
)


# ---------------------------------------------------------------------------------
# Members
admin.add_view(MemberView(Member, db.session, name="Members", endpoint="member"))
admin.add_view(
    CommitteeMeetingAttendanceView(
        CommitteeMeetingAttendance,
        db.session,
        name="Committee Meeting Attendances",
        endpoint="committeemeetingattendance",
        category="Committees",
    ),
)

# ---------------------------------------------------------------------------------
# Reports
admin.add_view(
    ReportView(name="General reports", endpoint="reports", category="Reports")
)
admin.add_view(
    UsageReportView(
        name="User usage report", endpoint="usage_report", category="Reports"
    )
)
admin.add_view(
    SubscriptionsView(category="Reports", name="Alert Counts", endpoint="subscriptions")
)
