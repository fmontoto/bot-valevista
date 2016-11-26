import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import models


engine = create_engine('sqlite:///db.sqlite')

models.Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

class ValeVistaBotException(Exception):
    def __init__(self, public_message):
        super(ValeVistaBotException, self).__init__(public_message)
        self.public_message = public_message

class DBError(ValeVistaBotException):
    pass

class UserBadUseError(ValeVistaBotException):
    pass

def commit_rollback(session):
    try:
        session.commit()
    except:
        session.rollback()
        raise

class User(object):
    @classmethod
    def _get_user(cls, telegram_id, create=True):
        user = session.query(models.User).filter_by(telegram_id=telegram_id).first()
        if not user:
            if not create:
                raise ValueError("User does not exists")
            user = models.User(telegram_id=telegram_id)
            session.add(user)
            session.commit()
        return user

    @classmethod
    def get_id(cls, telegram_id, create=True):
        """
        :param telegram_id: telegram id of the user to get.
        :param create: If true and the telegram id does not exists, creates a new user
        :return: the id of the user.
        """
        return cls._get_user(telegram_id, create).id

    @classmethod
    def set_rut(cls, telegram_id, rut):
        user = cls._get_user(telegram_id, True)
        if user.rut == rut:
            return
        user.rut = rut
        session.commit()

    @classmethod
    def get_rut(cls, telegram_id):
        user = cls._get_user(telegram_id, True)
        if user.rut:
            return user.rut
        return None

    @classmethod
    def is_subscribed(cls, telegram_id, chat_id):
        user_id = cls.get_id(telegram_id)
        result = session.query(models.SubscribedUsers).filter_by(user_id=user_id, chat_id=chat_id).all()
        return len(result) > 0

    @classmethod
    def subscribe(cls, telegram_id, chat_id):
        if not User.get_rut(telegram_id):
            raise UserBadUseError("Tienes que tener un rut registrado.")
        if User.is_subscribed(telegram_id, chat_id):
            raise UserBadUseError("Ya esta registrado")

        user_id = User.get_id(telegram_id, False)
        subscription = models.SubscribedUsers(user_id=user_id, chat_id=chat_id)
        session.add(subscription)
        commit_rollback(session)


    @classmethod
    def unsubscribe(cls, telegram_id, chat_id):
        user_id = cls.get_id(telegram_id, False)
        result = session.query(models.SubscribedUsers).filter_by(user_id=user_id, chat_id=chat_id).all()
        if not len(result):
            raise UserBadUseError("No estas suscrito")

        session.delete(result[0])
        session.commit()

    @classmethod
    def get_subscriber_not_retrieved_hours_ago(cls, hours):
        time_limit = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        already_updated_users = session.query(models.User).filter(
                models.SubscribedUsers.user_id == models.User.id).filter(
                models.CachedResult.user_id == models.User.id).filter(
                models.CachedResult.retrieved > time_limit)
        # All subscribed users minus the already updated
        to_update_users = session.query(models.User).filter(
                models.SubscribedUsers.user_id == models.User.id).filter(
                models.User.id.notin_(already_updated_users.with_entities(models.User.id)))
        return to_update_users.all()

class CachedResult(object):
    @classmethod
    def get(cls, user_id, rut):
        result = session.query(models.CachedResult).filter_by(user_id=user_id, rut=rut).all()
        if not result or result[0].retrieved < (datetime.datetime.utcnow() - datetime.timedelta(hours=2)):
            return None
        return result[0].result

    @classmethod
    def update(cls, user_id, rut, result):
        c_result = session.query(models.CachedResult).filter_by(user_id=user_id, rut=rut).all()
        if not c_result:
            c_result = models.CachedResult(rut=rut, user_id=user_id, result=result)
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
