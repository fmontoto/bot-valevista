from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import models, model_interface
from src.model_interface import User, CachedResult, UserBadUseError


class TestModelInterface(TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
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
        self.session = sessionmaker(bind=self.engine)()
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
        self.fail("Not implemented")

