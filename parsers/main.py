
class MyParser():

    def __init__(self):
        print "i'm a parser"

    def remove_html(self, html_str):

        return html_str


class MeetingReportParser(MyParser):

    def extract_title(self, str_in):
        return str_in

    def extract_committee(self, str_in):
        return str_in

    def extract_summary(self, str_in):
        return str_in

    def extract_related_docs(self, str_in):
        return str_in

    def extract_body(self, str_in):
        return str_in