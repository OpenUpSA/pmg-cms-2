
class MyParser():

    def __init__(self):
        print "i'm a parser"

    def strip_rtf(self, rtf_str):
        if rtf_str:
            return rtf_str.replace('\\"', '').replace('\\r', '').replace('\\n', '').replace('\\t', '')
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
        self.summary = None
        self.body = None
        self.related_docs = None
        self.related_bills = None
        if report_dict.get('minutes'):
            self.minutes_clean = self.strip_rtf(report_dict['minutes'])
        else:
            self.minutes_clean = None
        self.extract_title()
        self.extract_summary()
        self.extract_body()

    def extract_title(self):
        self.title = self.strip_rtf(self.title)
        return

    def extract_committee(self):
        return

    def extract_summary(self):
        return

    def extract_related_docs(self):
        return

    def extract_body(self):
        self.body = self.minutes_clean
        return


