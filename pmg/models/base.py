from inflection import underscore, dasherize
from flask import url_for

resource_slugs = {}

class ApiResource(object):
    """ Mixin that defines some helpers for resources that we expose
    directly through the API. 

    Resources must be registered by calling :func:`register`.
    """
    
    @property
    def url(self):
        return url_for('api.resource_list', resource=self.slug_prefix, resource_id=self.id, _external=True)

    @classmethod
    def list(cls):
        raise NotImplementedError()

    @classmethod
    def register(cls, target):
        name = target.__name__

        if not hasattr(target, 'resource_content_type'):
            # The underscored content_type for this resource. Used primarily by ElasticSearch.
            target.resource_content_type = underscore(name)

        if not hasattr(target, 'slug_prefix'):
            # The prefix for url slugs
            target.slug_prefix = dasherize(target.resource_content_type)

        resource_slugs[target.slug_prefix] = target


class FileLinkMixin(object):
    """ Mixin for models that link a content type to a File object
    in a many-to-many relationship.
    """

    def to_dict(self, include_related=False):
        """ Delegate to the file's to_dict completely. """
        return self.file.to_dict(include_related)
