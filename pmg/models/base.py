from inflection import underscore, dasherize

resource_slugs = {}

class ApiResource(object):
    """ Mixin that defines some helpers for resources that we expose
    directly through the API. 

    Resources must be registered by calling :func:`register`.
    """
    
    def url_path(self):
        return '/%s/%s' % (self.slug_prefix, self.id)

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
