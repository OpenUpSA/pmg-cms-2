from backend.app import logger
from datetime import datetime
import json


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


class MeetingReportParser(MyParser):

    def __init__(self, report_dict):
        self.source = report_dict
        self.title = None
        self.committee = None
        self.date = None
        if report_dict.get('meeting_date'):
            try:
                timestamp = int(report_dict['meeting_date'].strip('"'))
                self.date = datetime.fromtimestamp(
                timestamp
                )
            except (TypeError, AttributeError) as e:
                pass
        self.summary = None
        self.body = None
        self.related_docs = []
        self.audio = []
        self.related_bills = []

        self.extract_title()
        self.extract_committee()
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

    def extract_summary(self):
        self.summary = None
        if self.source.get('summary'):
            self.summary = self.strip_rtf(self.source['summary'])
        return

    def extract_related_docs(self):
        tmp = []
        for file in self.source['files']:
            if not file["fid"] in tmp:
                tmp.append(file["fid"])
                self.related_docs.append(file)
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


