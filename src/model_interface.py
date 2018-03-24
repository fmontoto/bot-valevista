"""Interface to talk with the db models."""
import datetime
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.messages import Messages
from src.utils import Rut
from . import models


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ValeVistaBotException(Exception):
    """Base exception, carries a public message for the user."""
    def __init__(self, public_message):
        super(ValeVistaBotException, self).__init__(public_message)
        self.public_message = public_message


class UserBadUseError(ValeVistaBotException):
    """User trying to do an invalid operation."""
    pass


class UserDoesNotExistError(ValeVistaBotException):
    """User not found in the DB."""
    pass


class DbConnection(object):
    """Connection to the database."""
    def __init__(self, in_memory: bool = False) -> None:
        if in_memory:
            engine = create_engine('sqlite:///:memory:')
        else:
            engine = create_engine('sqlite:///db.sqlite')

        models.Base.metadata.create_all(engine)
        self._session = scoped_session(sessionmaker(bind=engine))

    @staticmethod
    def commit_rollback(session):
        """Try to commit and rollback on failure."""
        try:
            session.commit()
        except Exception as commit_exep:
            session.rollback()
            logger.exception(commit_exep)
            raise commit_exep

    def get_session(self):
        """Returns a new SQLAlchemy session."""
        return self._session()


class User(object):
    """Interface to the User table in the database."""
    def __init__(self, db_connection: DbConnection) -> None:
        self._db_connection = db_connection

    def _get_user(self, telegram_id: int, create: bool = True):
        session = self._db_connection.get_session()
        user = session.query(
                models.User).filter_by(telegram_id=telegram_id).first()
        if not user:
            if not create:
                raise UserDoesNotExistError('User not found.')
            user = models.User(telegram_id=telegram_id)
            session.add(user)
            session.commit()
        return user

    def get_id(self, telegram_id: int, create: bool = True):
        """
        :param telegram_id: telegram id of the user to get.
        :param create: If true and the telegram id does not exists,
                       creates a new user
        :return: the id of the user.
        """
        return self._get_user(telegram_id, create).id

    def get_telegram_id(self, user_id):
        """Gets the telegram id for the given user."""
        session = self._db_connection.get_session()
        user = session.query(models.User).filter_by(id=user_id).first()
        if not user:
            raise UserDoesNotExistError('User not found.')
        return user.telegram_id

    def set_rut(self, telegram_id, rut):
        """Sets a rut for the user."""
        session = self._db_connection.get_session()
        user = self._get_user(telegram_id, True)
        if user.rut == rut.rut_sin_digito:
            return
        user.rut = rut.rut_sin_digito
        session.commit()

    def get_rut(self, telegram_id):
        """Gets the user rut."""
        user = self._get_user(telegram_id, True)
        if user.rut:
            return Rut.build_rut_sin_digito(user.rut)
        return None

    def is_subscribed(self, telegram_id, chat_id):
        """Whether the user with the given chat is subscribed or not."""
        session = self._db_connection.get_session()
        user_id = self.get_id(telegram_id)
        result = session.query(models.SubscribedUsers).filter_by(
                user_id=user_id, chat_id=chat_id).all()
        return len(result) > 0

    def subscribe(self, telegram_id, chat_id):
        """Subscribes the given user with the given chat."""
        if not self.get_rut(telegram_id):
            raise UserBadUseError(Messages.SUBSCRIBE_NO_RUT)
        if self.is_subscribed(telegram_id, chat_id):
            raise UserBadUseError(Messages.ALREADY_SUBSCRIBED)

        user_id = self.get_id(telegram_id, False)
        subscription = models.SubscribedUsers(user_id=user_id, chat_id=chat_id)
        session = self._db_connection.get_session()
        session.add(subscription)
        DbConnection.commit_rollback(session)

    def unsubscribe(self, telegram_id, chat_id):
        """Unsubscribes the user with the given id and chat."""
        user_id = self.get_id(telegram_id, False)
        session = self._db_connection.get_session()
        result = session.query(models.SubscribedUsers). \
            filter_by(user_id=user_id, chat_id=chat_id).all()
        if not result:
            raise UserBadUseError(Messages.UNSUBSCRIBE_NON_SUBSCRIBED)

        session.delete(result[0])
        session.commit()

    def get_subscribers_to_update(self, hours):
        """Subscribed users which results have not been retrieved in 'hours'.

        Returns  a list of all the subscribed users which cache has not been
        updated in the last 'hours' hours.
        """
        session = self._db_connection.get_session()
        t_limit = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        already_updated_users = session.query(models.User) \
            .filter(models.SubscribedUsers.user_id == models.User.id) \
            .filter(models.CachedResult.user_id == models.User.id) \
            .filter(models.CachedResult.retrieved > t_limit)
        # All subscribed users minus the already updated
        to_update_users = session.query(models.User) \
            .filter(models.SubscribedUsers.user_id == models.User.id) \
            .filter(models.User.id.notin_(
                    already_updated_users.with_entities(models.User.id)))
        return to_update_users.all()

    def get_chat_id(self, user_id):
        """Gets the chat id for the user with 'user_id'."""
        session = self._db_connection.get_session()
        subscribed_user = session.query(models.SubscribedUsers). \
            filter(models.SubscribedUsers.user_id == user_id).first()
        if subscribed_user is None:
            raise ValueError("User isn't subscribed")
        return subscribed_user.chat_id


class Cache(object):
    """Access to the cache db table."""
    def __init__(self, db_connection: DbConnection,
                 exp_time: datetime.timedelta = datetime.timedelta(
                         hours=2)) -> None:
        self._exp_time = exp_time
        self._db_connection = db_connection

    def get(self, user_id, rut):
        """If there are non expired results, return them."""
        session = self._db_connection.get_session()
        result = session.query(models.CachedResult).filter_by(
                user_id=user_id, rut=rut.rut_sin_digito).all()
        if not result or result[0].retrieved < (
                datetime.datetime.utcnow() - self._exp_time):
            return None
        return result[0].result

    def update(self, user_id, rut: Rut, result):
        """Updates the cache with 'result'.

        Returns:
            bool: Whether the cache changed or not (ie result was already
                stored).
        """
        session = self._db_connection.get_session()
        c_result = session.query(models.CachedResult).filter_by(
                user_id=user_id, rut=rut.rut_sin_digito).all()
        if not c_result:
            c_result = models.CachedResult(
                    rut=rut.rut_sin_digito, user_id=user_id, result=result)
            session.add(c_result)
            session.commit()
            return True
        if len(c_result) > 1:
            logger.warning("Unexpected len of results in the db:%d",
                           len(c_result))
        # If the new result is the same than the previous one onupdate is not
        # triggered and the timestamp of the cached result is not updated.
        if c_result[0].result == result:
            changed = False
        else:
            c_result[0].result = result
            changed = True
        c_result[0].retrieved = datetime.datetime.utcnow()
        session.commit()
        return changed
