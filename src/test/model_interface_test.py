from contextlib import ContextDecorator
import unittest
from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src import models, model_interface
from src.utils import Rut
from src.model_interface import User, Cache, UserBadUseError


class mock_model_interface(ContextDecorator):
    def __enter__(self):
        model_interface._start(in_memory=True)

    def __exit__(self, *exc):
        model_interface._start(in_memory=False)


class TestModelInterface(TestCase):

    def setUp(self):
        model_interface._start(in_memory=True)
        self.rut1 = Rut.build_rut('2.343.234-k')
        self.rut2 = Rut.build_rut('12.444.333-4')
        self.rut3 = Rut.build_rut('18.123.021-5')
        self.rut4 = Rut.build_rut('12.456.371-2')
        self.assertNotEqual(None, self.rut1)
        self.assertNotEqual(None, self.rut2)
        self.assertNotEqual(None, self.rut3)
        self.assertNotEqual(None, self.rut4)

    def tearDown(self):
        model_interface._start()

    def testGetUserId(self):
        self.assertRaises(model_interface.UserDoesNotExistError,
                          User.get_id, 2342, False)
        new_id = User.get_id(2342, True)
        self.assertEqual(new_id, User.get_id(2342, False))
        self.assertNotEqual(new_id, User.get_id(2351, True))

    def testCacheResult(self):
        result = "stored_result"
        result2 = "stored_result2"
        user_id = User.get_id(9, True)
        cache = Cache()
        self.assertIsNone(cache.get(user_id, self.rut1))
        cache.update(user_id, self.rut1, result)
        self.assertEqual(result, cache.get(user_id, self.rut1))
        cache.update(user_id, self.rut1, result2)
        self.assertEqual(result2, cache.get(user_id, self.rut1))

    def testRutSetAndGet(self):
        self.assertIsNone(User.get_rut(32))
        User.set_rut(32, self.rut1)
        self.assertEqual(self.rut1, User.get_rut(32))
        User.set_rut(32, self.rut2)
        self.assertEqual(self.rut2, User.get_rut(32))

    def testGetTelegramId(self):
        self.assertRaises(model_interface.UserDoesNotExistError,
                          User.get_telegram_id, 3)
        User.set_rut(23, self.rut1)
        user_id = User.get_id(23, False)
        self.assertEqual(23, User.get_telegram_id(user_id))


class TestSubscription(TestCase):

    def setUp(self):
        model_interface._start(in_memory=True)
        self.rut1 = Rut.build_rut('2.343.234-k')
        self.rut2 = Rut.build_rut('12.444.333-4')
        self.rut3 = Rut.build_rut('18.123.021-5')
        self.rut4 = Rut.build_rut('12.456.371-2')
        self.assertNotEqual(None, self.rut1)
        self.assertNotEqual(None, self.rut2)
        self.assertNotEqual(None, self.rut3)
        self.assertNotEqual(None, self.rut4)

    def tearDown(self):
        model_interface._start()

    def testSimpleSubscribeUnsubscribe(self):
        telegram_id = 34
        chat_id = 5657
        telegram_id2 = 35
        chat_id2 = 5658
        # User isn't subscribed
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        # User does not have a registered rut
        self.assertRaises(UserBadUseError, User.subscribe, telegram_id,
                          chat_id)
        self.assertIsNone(User.set_rut(telegram_id, self.rut1))
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(User.subscribe(telegram_id, chat_id))
        self.assertTrue(User.is_subscribed(telegram_id, chat_id))
        self.assertRaises(UserBadUseError, User.subscribe, telegram_id,
                          chat_id)
        self.assertIsNone(User.unsubscribe(telegram_id, chat_id))
        self.assertFalse(User.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(User.subscribe(telegram_id, chat_id))
        self.assertIsNone(User.set_rut(telegram_id2, self.rut2))
        self.assertFalse(User.is_subscribed(telegram_id2, chat_id2))
        self.assertRaises(sqlalchemy.exc.IntegrityError, User.subscribe,
                          telegram_id, chat_id2)
        self.assertRaises(sqlalchemy.exc.IntegrityError, User.subscribe,
                          telegram_id2, chat_id)
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

        User.set_rut(telegram_id, self.rut1)
        User.set_rut(telegram_id2, self.rut2)
        User.set_rut(telegram_id3, self.rut3)
        User.set_rut(telegram_id4, self.rut4)
        User.subscribe(telegram_id, chat_id)
        User.subscribe(telegram_id2, chat_id2)
        User.subscribe(telegram_id3, chat_id3)

        cache = Cache()
        cache.update(User.get_id(telegram_id), self.rut1, "result")
        cache.update(User.get_id(telegram_id2), self.rut2, "result2")

        self.assertTrue(User.is_subscribed(telegram_id, chat_id))
        self.assertTrue(User.is_subscribed(telegram_id2, chat_id2))
        self.assertEqual(1,
                         len(User.get_subscriber_not_retrieved_hours_ago(2)))
        self.assertEqual(3,
                         len(User.get_subscriber_not_retrieved_hours_ago(0)))
        self.assertEqual("%s" % chat_id,
                         User.get_chat_id(User.get_id(telegram_id)))


if __name__ == '__main__':
    unittest.main()
