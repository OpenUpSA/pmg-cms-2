from wtforms.validators import ValidationError
from mock import MagicMock

from tests import PMGTestCase
from pmg.admin.validators import BillEventTitleAllowed


class TestValidators(PMGTestCase):
    def test_invalid_bill_event_title_allowed(self):
        validator = BillEventTitleAllowed()
        event_type = MagicMock(data='bill-passed')
        event_title = MagicMock(data='Test title')
        form = {'type': event_type}
        self.assertRaises(ValidationError, validator, form, event_title)

    def test_valid_bill_event_title_allowed(self):
        validator = BillEventTitleAllowed()
        event_type = MagicMock(data='bill-passed')
        event_title = MagicMock(
            data='Bill passed by the National Assembly and transmitted to the NCOP for concurrence')
        form = {'type': event_type}

        try:
            validator(form, event_title)
        except:
            self.fail(
                'BillEventTitleAllowed validator should not fail for '
                'event title "%s" with event type "%s".' % (
                    event_type.data,
                    event_title.data,
                ))
