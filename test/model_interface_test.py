from contextlib import ContextDecorator
from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src import models, model_interface
from src.model_interface import User, CachedResult, UserBadUseError

class mock_model_interface(ContextDecorator):
    def __enter__(self):
        self.engine = create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(self.engine)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        self.old_session = model_interface.session
        model_interface.session = self.session
        return self

    def __exit__(self, *exc):
        model_interface.session = self.old_session


class TestModelInterface(TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(self.engine)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        self.old_session = model_interface.session
        model_interface.session = self.session

    def tearDown(self):
        model_interface.session = self.old_session

    def testGetUserId(self):
        self.assertRaises(ValueError, User.get_id, 2342, False)
        new_id = User.get_id(2342, True)
        self.assertEqual(new_id, User.get_id(2342, False))
        self.assertNotEqual(new_id, User.get_id(2351, True))

    def testCachedResult(self):
        rut = "12345634"
        result = "stored_result"
        result2 = "stored_result2"
        user_id = User.get_id(9, True)
        self.assertIsNone(CachedResult.get(user_id, rut))
        CachedResult.update(user_id, rut, result)
        self.assertEqual(result, CachedResult.get(user_id, rut))
        CachedResult.update(user_id, rut, result2)
        self.assertEqual(result2, CachedResult.get(user_id, rut))

    def testRutSetAndGet(self):
        self.assertIsNone(User.get_rut(32))
        User.set_rut(32, "12345678")
        self.assertEqual("12345678", User.get_rut(32))
        User.set_rut(32, "12345679")
        self.assertEqual("12345679", User.get_rut(32))

class TestSubscription(TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(self.engine)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        self.old_session = model_interface.session
        model_interface.session = self.session

    def tearDown(self):
        model_interface.session = self.old_session

    def testSimpleSubscribeUnsubscribe(self):
        telegram_id = 34
        chat_id = 5657
        telegram_id2 = 35
        chat_id2 = 5658
        # User isn't subscribed
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        # User does not have a registered rut
        self.assertRaises(UserBadUseError, User.subscribe, telegram_id, chat_id)
        self.assertIsNone(User.set_rut(telegram_id, 28194837))
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(User.subscribe(telegram_id, chat_id))
        self.assertTrue(User.is_subscribed(telegram_id, chat_id))
        self.assertRaises(UserBadUseError, User.subscribe, telegram_id, chat_id)
        self.assertIsNone(User.unsubscribe(telegram_id, chat_id))
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(User.subscribe(telegram_id, chat_id))
        self.assertIsNone(User.set_rut(telegram_id2, 28194837))
        self.assertFalse(User.is_subscribed(telegram_id2, chat_id2))
        self.assertRaises(sqlalchemy.exc.IntegrityError, User.subscribe, telegram_id, chat_id2)
        self.assertRaises(sqlalchemy.exc.IntegrityError, User.subscribe, telegram_id2, chat_id)
        self.assertIsNone(User.subscribe(telegram_id2, chat_id2))

    def testGetSubscribersToUpdate(self):
        telegram_id = 23
        telegram_id2 = 24
        telegram_id3 = 25
        telegram_id4 = 26
        chat_id = 33
        chat_id2 = 34
        chat_id3 = 35
        chat_id4 = 36
        rut = 18392843
        rut2 = 62719201
        rut3 = 73829365
        rut4 = 83927162

        User.set_rut(telegram_id, rut)
        User.set_rut(telegram_id2, rut2)
        User.set_rut(telegram_id3, rut3)
        User.set_rut(telegram_id4, rut4)
        User.subscribe(telegram_id, chat_id)
        User.subscribe(telegram_id2, chat_id2)
        User.subscribe(telegram_id3, chat_id3)

        CachedResult.update(User.get_id(telegram_id), rut, "result")
        CachedResult.update(User.get_id(telegram_id2), rut2, "result2")

        self.assertTrue(User.is_subscribed(telegram_id, chat_id))
        self.assertTrue(User.is_subscribed(telegram_id2, chat_id2))
        self.assertEqual(1, len(User.get_subscriber_not_retrieved_hours_ago(2)))
        self.assertEqual(3, len(User.get_subscriber_not_retrieved_hours_ago(0)))
