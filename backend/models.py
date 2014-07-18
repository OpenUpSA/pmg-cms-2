import sqlalchemy
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

engine = create_engine('sqlite:///instance/tmp.db')

Base = declarative_base()


def __content_type_repr__(self):
    return "<Content_type(pk='%s')>" % self.pk


def get_content_type_model(model_name, fields, model=Base):
    """
    Meta-class for generating database model classes.
    Creates models on the fly, using the builtin 'type' metaclass, see
    http://stackoverflow.com/questions/100003/what-is-a-metaclass-in-python
    """

    field_defs = {
        '__tablename__': model_name.lower(),
        '__repr__': __content_type_repr__,
        'pk': Column(Integer, primary_key=True),
        }

    for field in fields:
        field_defs[field] = Column(String)

    tmp = type(model_name, (model,), field_defs)

    # create the database table if necessary
    Base.metadata.create_all(engine)
    return tmp


def generate_models():

    model_defs = [
        ('bill', [u'_id', u'audio', u'bill_tracker_link_attributes', u'bill_tracker_link_title', u'bill_tracker_link_url', u'content_type', u'delta', u'effective_date', u'file_bill_data', u'file_bill_description', u'file_bill_fid', u'file_bill_list', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'version', u'vid']),
        ('billsstatus', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('briefing', [u'_id', u'audio', u'audio_reference_nid', u'briefing_date', u'content_type', u'delta', u'document_other', u'document_other_format', u'files', u'minutes', u'minutes_format', u'nid', u'presentation', u'presentation_format', u'revisions', u'start_date', u'summary', u'summary_format', u'tagline', u'terms', u'title', u'vid']),
        ('calls_comment_public_hearings', [u'_id', u'audio', u'comment_exp', u'comment_exp2', u'comment_type', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('comm_info_page', [u'_id', u'audio', u'comm_info_type', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('comm_programme', [u'_id', u'audio', u'comm_programme_data', u'comm_programme_fid', u'comm_programme_list', u'content_type', u'delta', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('committee_member', [u'_id', u'audio', u'commem_img_data', u'commem_img_fid', u'commem_img_list', u'content_type', u'delta', u'files', u'mp_adhoc_altmem', u'mp_adhoc_chair', u'mp_adhoc_mem', u'mp_altmember', u'mp_chairperson', u'mp_email_email', u'mp_joint_altmem', u'mp_joint_chair', u'mp_joint_mem', u'mp_link_attributes', u'mp_link_title', u'mp_link_url', u'mp_member', u'mp_ncop_altmem', u'mp_ncop_chair', u'mp_ncop_mem', u'mp_party', u'mp_province', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('daily_schedule', [u'_id', u'audio', u'content_type', u'daily_sched_date', u'embedded_pdf_data', u'embedded_pdf_fid', u'embedded_pdf_list', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('faq', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('gazette', [u'_id', u'audio', u'content_type', u'effective_date', u'file_gazette_data', u'file_gazette_description', u'file_gazette_fid', u'file_gazette_list', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('hansard', [u'_id', u'audio', u'content_type', u'files', u'meeting_date', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('home_image', [u'_id', u'audio', u'content_type', u'files', u'home_image_data', u'home_image_fid', u'home_image_list', u'homeimg_link', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('mp_blog', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('newsletter', [u'_id', u'audio', u'content_type', u'delta', u'embedded_pdf_data', u'embedded_pdf_fid', u'embedded_pdf_list', u'files', u'newsletter_edition', u'newsletter_edition_month', u'newsletter_headline', u'newsletter_image_data', u'newsletter_image_fid', u'newsletter_image_list', u'newsletter_lead', u'newsletter_lead_format', u'newsletter_type', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('page', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('pmg_contact', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('policy_document', [u'_id', u'audio', u'content_type', u'effective_date', u'file_policy_doc_data', u'file_policy_doc_description', u'file_policy_doc_fid', u'file_policy_doc_list', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('programme', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('questions_replies', [u'_id', u'audio', u'content_type', u'files', u'nid', u'question_number', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('report', [u'_id', u'audio', u'chairperson', u'content_type', u'files', u'meeting_date', u'minutes', u'minutes_format', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ('tabled_committee_reports', [u'_id', u'audio', u'content_type', u'files', u'nid', u'revisions', u'start_date', u'terms', u'title', u'vid']),
        ]

    model_dict = {}

    for name, fields in model_defs:
        model_dict[name] = get_content_type_model(name, fields)

    return model_dict


if __name__ == "__main__":

    model_name = 'bill'
    fields = [u'files', u'audio', u'terms', u'vid', u'title', u'file_bill_fid', u'file_bill_list', u'nid', u'bill_tracker_link_attributes', u'file_bill_description', u'version', u'bill_tracker_link_title', u'content_type', u'delta', u'effective_date', u'file_bill_data', u'_id', u'start_date', u'bill_tracker_link_url', u'revisions']

    model = get_content_type_model(model_name, fields)
