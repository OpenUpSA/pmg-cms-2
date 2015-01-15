from backend.app import logging
from datetime import datetime, time
import json
from dateutil import tz


class MyParser():

    def __init__(self):
        print "i'm a parser"

    def strip_rtf(self, rtf_str):
        if rtf_str:
            return unicode(rtf_str.replace('\\"', '').replace('\\r', '').replace('\\n', '').replace('\\t', ''))
        else:
            return None

    def remove_html(self, html_str):

        return html_str

    def unpack_field_document_data(self, str_in):
        out = {}
        tmp = str_in.split('\"')
        # logger.debug(tmp)
        # file description
        i = tmp.index('description')
        if i >= 0:
            out['description'] = tmp[i+2]
        return out

class MeetingReportParser(MyParser):

    def __init__(self, report_dict):
        self.source = report_dict
        self.title = None
        self.committee = None
        self.date = None
        self.chairperson = None
        if report_dict.get('meeting_date'):
            try:
                timestamp = int(report_dict['meeting_date'].strip('"'))
                tmp = datetime.fromtimestamp(timestamp).date()
                tmp = datetime.combine(tmp, time(0, 0))
                tmp = tmp.replace(tzinfo=tz.gettz('utc'))
                self.date = tmp
            except (TypeError, AttributeError) as e:
                pass
        self.summary = None
        self.body = None
        self.related_docs = []
        self.audio = []
        self.related_bills = []

        self.extract_title()
        self.extract_committee()
        self.extract_chairperson()
        self.extract_summary()
        self.extract_related_docs()
        self.extract_audio()
        self.extract_body()

    def extract_title(self):
        self.title = self.strip_rtf(self.source['title'])
        return

    def extract_committee(self):
        if self.source['terms']:
            self.committee = self.strip_rtf(self.source['terms'][0])
        return

    def extract_chairperson(self):
        if self.source.get('chairperson'):
            self.chairperson = self.strip_rtf(self.source['chairperson'])
        return

    def extract_summary(self):
        self.summary = None
        if self.source.get('summary'):
            self.summary = self.strip_rtf(self.source['summary'])
        return

    def extract_related_docs(self):
        tmp_list = []
        for file in self.source['files']:
            if file["filepath"].startswith('files/'):
                file["filepath"] = file["filepath"][6::]
            # duplicate entries exist, but they don't both have all of the detail
            if not file["fid"] in tmp_list:
                tmp_list.append(file["fid"])
                self.related_docs.append(file)
            # update the document title
            i = tmp_list.index(file["fid"])
            doc = self.related_docs[i]
            if file.get("field_document_data"):
                tmp_data = self.unpack_field_document_data(file["field_document_data"])
                if tmp_data.get("description"):
                    doc["title"] = tmp_data.get("description")
            if file.get("field_document_description"):
                doc["title"] = file.get("field_document_description")
            elif not doc.get("title") and file.get("filename"):
                doc["title"] = file.get("filename")
            elif not doc.get("title") and file.get("origname"):
                doc["title"] = file.get("origname")
            elif not doc.get("title"):
                doc["title"] = "Unnamed document"
        return

    def extract_audio(self):
        tmp = []
        for file in self.source['audio']:
            if not file["fid"] in tmp:
                tmp.append(file["fid"])
                self.audio.append(file)
        return

    def extract_body(self):
        if self.source.get('minutes'):
            minutes_clean = self.strip_rtf(self.source['minutes'])
        else:
            minutes_clean = None
        self.body = minutes_clean
        return


