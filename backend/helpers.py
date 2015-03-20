import logging

from frontend import app

logger = logging.getLogger(__name__)

@app.context_processor
def inject_paths():
    context_vars = {
        'FRONTEND_HOST': app.config['FRONTEND_HOST'],
        'API_HOST': app.config['API_HOST'],
        'STATIC_HOST': app.config['STATIC_HOST'],
        }
    return context_vars


@app.template_filter('add_commas')
def jinja2_filter_add_commas(quantity):
    out = ""
    quantity_str = str(quantity)
    while len(quantity_str) > 3:
        tmp = quantity_str[-3::]
        out = "," + tmp + out
        quantity_str = quantity_str[0:-3]
    return quantity_str + out


@app.template_filter('dir')
def jinja2_filter_dir(value):
    res = []
    for k in dir(value):
        res.append('%r %r\n' % (k, getattr(value, k)))
    return '<br>'.join(res)


@app.template_filter('is_file')
def jinja2_filter_is_file(content_obj):
    logger.debug("IS_FILE")
    logger.debug(content_obj)
    if content_obj.file:
        return True
    return False
