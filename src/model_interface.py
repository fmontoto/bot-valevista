import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import models
from .models import Base, CachedResult, User


engine = create_engine('sqlite:///db.sqlite')

Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

class DBException(Exception):
    def __init__(self, public_message):
        super(DBException, self).__init__(public_message)
        self.public_message = public_message

def get_user_id(telegram_id, create=True):
    """
    :param telegram_id: telegram id of the user to get.
    :param create: If true and the telegram id does not exists, creates a new user
    :return: the id of the user.
    """
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        if not create:
            raise ValueError("User does not exists")
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
    return user.id

def cached_result(user, rut):
    result = session.query(CachedResult).filter_by(user_id=user.id, rut=rut)
    if not result or result.retrieved < (datetime.datetime.now() - datetime.timedelta(hours=2)):
        return None
    return result.result

def update_cached_result(user, rut, result):
    c_result = session.query(CachedResult).filter_by(user_id=user.id, rut=rut)
    if not c_result:
        c_result = CachedResult(rut=rut, user_id=user.id, result=result)
        session.add(c_result)
        session.commit()
    c_result.result = result
    session.commit()