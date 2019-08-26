from wtforms.validators import AnyOf
from wtforms.compat import string_types, text_type


class BillEventTitleAllowed(object):
    """
    Checks that the bill event title is one of the allowed titles when the 
    event type is "bill-passed".
    """
    ALLOWED_TITLES = [
        'Bill passed by the National Assembly and transmitted to the NCOP for concurrence',
        'Bill passed by both Houses and sent to President for assent',
        'Bill passed by the NCOP and returned to the National Assembly for concurrence',
        'Bill passed and amended by the NCOP and returned to the National Assembly for concurrence',
        'Bill passed by the NCOP and sent to the President for assent',
        'The NCOP rescinded its decision',
        'Bill remitted',
        'Bill revived on this date'
    ]

    def __call__(self, form, field):
        bill_type = form['type']
        if bill_type.data == 'bill-passed':
            message = 'When event type is "Bill passed", event title must be one of: %(values)s.'
            any_of = AnyOf(self.ALLOWED_TITLES, message=message,
                           values_formatter=self.values_formatter)
            return any_of(form, field)

    @classmethod
    def values_formatter(cls, values):
        return ', '.join(cls.quoted(text_type(x)) for x in values)

    @classmethod
    def quoted(cls, value):
        return '"%s"' % value
