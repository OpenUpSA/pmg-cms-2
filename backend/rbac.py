import urllib

from flask import redirect
from flask.ext.security import current_user

class RBACMixin(object):
    """ Role-based access control for views. """

    # if False, we don't require authentication at all
    require_authentication = True
    # user must have all of these roles
    required_roles = []

    def is_accessible(self):
        if not self.require_authentication:
            return True

        if not current_user.is_active() or not current_user.is_authenticated():
            return False

        if all(current_user.has_role(r) for r in self.required_roles):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            tmp = '/security/login?next=' + urllib.quote_plus(request.base_url)
            return redirect(tmp, code=302)



