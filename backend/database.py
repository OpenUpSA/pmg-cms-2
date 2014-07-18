from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///instance/tmp.db')
Session = sessionmaker(bind=engine)
session = Session()