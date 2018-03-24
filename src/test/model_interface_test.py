from contextlib import ContextDecorator
import unittest
from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src import models, model_interface
from src.utils import Rut
from src.model_interface import DbConnection, User, Cache, UserBadUseError


class TestModelInterface(TestCase):

    def setUp(self):
        self._db_connection = DbConnection(in_memory=True)
        self._user = User(self._db_connection)
        self.rut1 = Rut.build_rut('2.343.234-k')
        self.rut2 = Rut.build_rut('12.444.333-4')
        self.rut3 = Rut.build_rut('18.123.021-5')
        self.rut4 = Rut.build_rut('12.456.371-2')
        self.assertNotEqual(None, self.rut1)
        self.assertNotEqual(None, self.rut2)
        self.assertNotEqual(None, self.rut3)
        self.assertNotEqual(None, self.rut4)

    def testGetUserId(self):
        self.assertRaises(model_interface.UserDoesNotExistError,
                          self._user.get_id, 2342, False)
        new_id = self._user.get_id(2342, True)
        self.assertEqual(new_id, self._user.get_id(2342, False))
        self.assertNotEqual(new_id, self._user.get_id(2351, True))

    def testCacheResult(self):
        result = "stored_result"
        result2 = "stored_result2"
        user_id = self._user.get_id(9, True)
        cache = Cache(self._db_connection)
        self.assertIsNone(cache.get(user_id, self.rut1))
        cache.update(user_id, self.rut1, result)
        self.assertEqual(result, cache.get(user_id, self.rut1))
        cache.update(user_id, self.rut1, result2)
        self.assertEqual(result2, cache.get(user_id, self.rut1))

    def testRutSetAndGet(self):
        self.assertIsNone(self._user.get_rut(32))
        self._user.set_rut(32, self.rut1)
        self.assertEqual(self.rut1, self._user.get_rut(32))
        self._user.set_rut(32, self.rut2)
        self.assertEqual(self.rut2, self._user.get_rut(32))

    def testGetTelegramId(self):
        self.assertRaises(model_interface.UserDoesNotExistError,
                          self._user.get_telegram_id, 3)
        self._user.set_rut(23, self.rut1)
        user_id = self._user.get_id(23, False)
        self.assertEqual(23, self._user.get_telegram_id(user_id))


class TestSubscription(TestCase):

    def setUp(self):
        self._db_connection = DbConnection(in_memory=True)
        self._user = User(self._db_connection)
        self.rut1 = Rut.build_rut('2.343.234-k')
        self.rut2 = Rut.build_rut('12.444.333-4')
        self.rut3 = Rut.build_rut('18.123.021-5')
        self.rut4 = Rut.build_rut('12.456.371-2')
        self.assertNotEqual(None, self.rut1)
        self.assertNotEqual(None, self.rut2)
        self.assertNotEqual(None, self.rut3)
        self.assertNotEqual(None, self.rut4)

    def testSimpleSubscribeUnsubscribe(self):
        telegram_id = 34
        chat_id = 5657
        telegram_id2 = 35
        chat_id2 = 5658
        # self._user isn't subscribed
        self.assertFalse(self._user.is_subscribed(telegram_id, chat_id))
        # self._user does not have a registered rut
        self.assertRaises(UserBadUseError, self._user.subscribe,
                          telegram_id, chat_id)
        self.assertIsNone(self._user.set_rut(telegram_id, self.rut1))
        self.assertFalse(self._user.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(self._user.subscribe(telegram_id, chat_id))
        self.assertTrue(self._user.is_subscribed(telegram_id, chat_id))
        self.assertRaises(UserBadUseError, self._user.subscribe,
                          telegram_id, chat_id)
        self.assertIsNone(self._user.unsubscribe(telegram_id, chat_id))
        self.assertFalse(self._user.is_subscribed(telegram_id, chat_id))
        self.assertIsNone(self._user.subscribe(telegram_id, chat_id))
        self.assertIsNone(self._user.set_rut(telegram_id2, self.rut2))
        self.assertFalse(self._user.is_subscribed(telegram_id2, chat_id2))
        self.assertRaises(sqlalchemy.exc.IntegrityError, self._user.subscribe,
                          telegram_id, chat_id2)
        self.assertRaises(sqlalchemy.exc.IntegrityError, self._user.subscribe,
                          telegram_id2, chat_id)
        self.assertIsNone(self._user.subscribe(telegram_id2, chat_id2))

    def testGetSubscribersToUpdate(self):
        telegram_id = 23
        telegram_id2 = 24
        telegram_id3 = 25
        telegram_id4 = 26
        chat_id = 33
        chat_id2 = 34
        chat_id3 = 35
        chat_id4 = 36

        self._user.set_rut(telegram_id, self.rut1)
        self._user.set_rut(telegram_id2, self.rut2)
        self._user.set_rut(telegram_id3, self.rut3)
        self._user.set_rut(telegram_id4, self.rut4)
        self._user.subscribe(telegram_id, chat_id)
        self._user.subscribe(telegram_id2, chat_id2)
        self._user.subscribe(telegram_id3, chat_id3)

        cache = Cache(self._db_connection)
        cache.update(self._user.get_id(telegram_id), self.rut1, "result")
        cache.update(self._user.get_id(telegram_id2), self.rut2, "result2")

        self.assertTrue(self._user.is_subscribed(telegram_id, chat_id))
        self.assertTrue(self._user.is_subscribed(telegram_id2, chat_id2))
        self.assertEqual(1, len(self._user.get_subscribers_to_update(2)))
        self.assertEqual(3, len(self._user.get_subscribers_to_update(0)))
        self.assertEqual("%s" % chat_id, self._user.get_chat_id(
                self._user.get_id(telegram_id)))

    def testGetChatId(self):
        telegram_id = 23
        telegram_id2 = 24
        telegram_id3 = 25
        chat_id = 33
        chat_id2 = 34
        chat_id3 = 35

        self._user.set_rut(telegram_id, self.rut1)
        self._user.set_rut(telegram_id2, self.rut2)
        self._user.set_rut(telegram_id3, self.rut3)

        self._user.subscribe(telegram_id, chat_id)
        self._user.subscribe(telegram_id2, chat_id2)
        self._user.subscribe(telegram_id3, chat_id3)

        self.assertEqual("%s" % chat_id, self._user.get_chat_id(
                self._user.get_id(telegram_id)))
        self.assertEqual("%s" % chat_id2, self._user.get_chat_id(
                self._user.get_id(telegram_id2)))

        self.assertEqual("%s" % chat_id3, self._user.get_chat_id(
                self._user.get_id(telegram_id3)))


if __name__ == '__main__':
    unittest.main()
