import datetime
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    rut = Column(String(length=9))

    def __repr__(self):
        return "<User(id='%s', telegram_id='%s')>" % (
                self.id, self.telegram_id)

class CachedResult(Base):
    __tablename__ = 'cached_results'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    rut = Column(String(length=9))
    retrieved = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    result = Column(String(length=250))

    def __repr__(self):
        return "<CachedResult(id='%s', user_id='%s', rut='%s', retrieved='%s', result='%s')>" % (
                self.id, self.user_id, self.rut, self.retrieved, self.result)
