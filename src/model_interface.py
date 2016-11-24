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

def _get_user(telegram_id, create=True):
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        if not create:
            raise ValueError("User does not exists")
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
    return user

def get_user_id(telegram_id, create=True):
    """
    :param telegram_id: telegram id of the user to get.
    :param create: If true and the telegram id does not exists, creates a new user
    :return: the id of the user.
    """
    return _get_user(telegram_id, create).id

def cached_result(user_id, rut):
    result = session.query(CachedResult).filter_by(user_id=user_id, rut=rut).all()
    if not result or result[0].retrieved < (datetime.datetime.utcnow() - datetime.timedelta(hours=2)):
        return None
    return result[0].result

def update_cached_result(user_id, rut, result):
    c_result = session.query(CachedResult).filter_by(user_id=user_id, rut=rut).all()
    if not c_result:
        c_result = CachedResult(rut=rut, user_id=user_id, result=result)
        session.add(c_result)
        session.commit()
        return
    # If the new result is the same than the previous one onupdate is not triggered and
    # the timestamp of the cached result is not updated.
    if c_result[0].result == result:
        c_result[0].retrieved = datetime.datetime.utcnow()
    else:
        c_result[0].result = result
    session.commit()

def set_user_rut(telegram_id, rut):
    user = _get_user(telegram_id, True)
    if user.rut == rut:
        return
    user.rut = rut
    session.commit()

def get_user_rut(telegram_id):
    user = _get_user(telegram_id, True)
    if user.rut:
        return user.rut
    return None
