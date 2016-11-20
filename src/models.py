import datetime
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)

class CachedResult(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id'))
    rut = String(length=9)
    retrieved = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    result = String(length=250)

engine = create_engine('sqlite:///db.sqlite')

Base.metadata.create_all(engine)