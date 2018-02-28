"""DB models used by the bot."""
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()  # pylint: disable=invalid-name


# pylint: disable=too-few-public-methods
class User(Base):  # type: ignore
    """Bot user."""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # internal id.
    # Must be set.
    telegram_id = Column(Integer, unique=True)
    # If set, must be the rut without digito verificador
    rut = Column(String(length=9))

    def __repr__(self):
        return "<User(id='%s', telegram_id='%s')>" % (
                self.id, self.telegram_id)


# pylint: disable=too-few-public-methods
class CachedResult(Base):  # type: ignore
    """Stores previously retrieved results.

    This helps to avoid consecutive queries to the bank service as well as
    checking if there are changes since the last time we queried the service.
    """
    __tablename__ = 'cached_results'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    rut = Column(String(length=9))
    retrieved = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now())
    # TODO(fmontoto): Increase this limit to at least 500, we already have
    # results with 240.
    result = Column(String(length=250))

    def __repr__(self):
        return ("<CachedResult(id='%s', user_id='%s', rut='%s', "
                "retrieved='%s', result='%s')>") % (self.id, self.user_id,
                                                    self.rut, self.retrieved,
                                                    self.result)


# pylint: disable=too-few-public-methods
class SubscribedUsers(Base):  # type: ignore
    """List of subscribed users."""
    __tablename__ = 'subscribed_users'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    chat_id = Column(String(length=20), unique=True)
