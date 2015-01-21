from flask.ext.admin import BaseView, expose
from models import EmailTemplate
from app import app, db

class EmailAlertView(BaseView):
    @expose('/')
    def index(self):
        templates = db.session.query(EmailTemplate).order_by(EmailTemplate.name).all()
        return self.render('admin/alerts/index.html',
                templates=templates)

    @expose('/new')
    def new(self):
        return self.render('admin/alerts/new.html')
