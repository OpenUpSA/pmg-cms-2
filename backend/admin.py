import models
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from app import app, db

model_dict = models.generate_models()

admin = Admin(app=app, name='PMG DATA', url='/')

model_names = model_dict.keys()
model_names.sort()

for name in model_names:
    admin.add_view(ModelView(model_dict[name], db.session, name=name.title(), endpoint=name))

