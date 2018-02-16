from datetime import datetime
from typing import Optional
import unittest
from unittest import TestCase
from unittest.mock import MagicMock
import telegram
import queue
from concurrent.futures import ThreadPoolExecutor

from src.test.model_interface_test import mock_model_interface
from src.bot import ValeVistaBot
from src.bot import add_handlers
from src.utils import is_a_proper_time, Rut
from src import model_interface
import pytz

from telegram.ext import CommandHandler, Handler, MessageHandler


class MockDispatcher(telegram.ext.Dispatcher):
    pass


id = 0


def get_id():
    global id
    id += 1
    return id

def dummyCb(*args, **kwargs):
    pass

def simpleCommand(bot, name: str, user: telegram.User, chat: telegram.Chat,
                  cb_reply=None,
                  message: Optional[str]=None) -> telegram.Update:
    msg = telegram.Message(get_id(), from_user=user,
                           date=datetime.now(), chat=chat,
                           text='/%s' % name,
                           reply_to_message=cb_reply, bot=bot)
    update = telegram.Update(get_id(), message=msg)
    update.message.reply_text = cb_reply
    return update


class TestBot(TestCase):
    def setUp(self):
        model_interface._start(True)
        self.bot = ValeVistaBot()
        self.queue = queue.Queue()
        self.dispatcher = MockDispatcher(self.bot, self.queue)
        self.user1 = telegram.User(id=get_id(), first_name='john',
                                   username='ujohn', is_bot=False)
        self.chat = telegram.Chat(get_id(), type='private', username='ujohn',
                                  first_name='john')
        add_handlers(self.dispatcher, self.bot)
        self.pass_test = True
        self.rut = Rut.build_rut('2343234-k')
        self.rut_non_std_str = '2343.234-k'

    def assertContains(self, string, substring):
        if substring in string:
            return
        print('"%s" not contained in "%s"' % (substring, string))
        self.assertTrue(False)

    def contains(self, expected_string, received_string):
        self.pass_test = expected_string in received_string

    def store_received_string(self, recv_str: str):
        self.stored = recv_str

    def simpleCommand(self, name: str, cb_reply=None,
                      message: Optional[str]=None):
        return simpleCommand(self.bot, name, self.user1, self.chat,
                             cb_reply, message)

    def simpleMessage(self, message: Optional[str]=None,
                      cb_reply=dummyCb):
        msg = telegram.Message(get_id(), from_user=self.user1,
                               date=datetime.now(), chat=self.chat,
                               text=message, reply_to_message=cb_reply)
        update = telegram.Update(get_id(), message=msg)
        return update

    def testStart(self):
        # Substring from start command
        expected = "Hola %s, soy el bot de los vale vista" % (
                self.user1.first_name)
        update = self.simpleCommand('start',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertContains(self.stored, expected)

    def testHelp(self):
        expected = ValeVistaBot._HELP_MSG
        update = self.simpleCommand('help',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testGetNoRutSet(self):
        expected = ValeVistaBot._NO_RUT_MSG
        update = self.simpleCommand('get', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetEmptyRut(self):
        expected = ValeVistaBot._SET_EMPTY_RUT
        update = self.simpleCommand('set', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetInvalidRut(self):
        expected = ValeVistaBot._SET_INVALID_RUT
        update = self.simpleCommand('set NO_VALID_RUT',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetRut(self):
        expected = ValeVistaBot._SET_RUT % str(self.rut)
        update = self.simpleCommand('set %s' % self.rut_non_std_str,
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

class TestFunctionalBot(TestCase):
    def setUp(self):
        model_interface._start(True)
        self.retriever = WebPageFromFileRetriever()
        self.bot = ValeVistaBot(self.retriever)
        self.queue = queue.Queue()
        self.dispatcher = MockDispatcher(self.bot, self.queue)
        self.user1 = telegram.User(id=get_id(), first_name='john',
                                   username='ujohn', is_bot=False)
        self.chat = telegram.Chat(get_id(), type='private', username='ujohn',
                                  first_name='john')
        add_handlers(self.dispatcher, self.bot)
        self.pass_test = True
        self.rut = Rut.build_rut('2343234-k')
        self.rut2 = Rut.build_rut('12444333-4')

    def setRut(self):
        update = self.simpleCommand('set %s' % self.rut)
        self.dispatcher.process_update(update)

    def simpleCommand(self, name: str, cb_reply=None,
                      message: Optional[str]=None):
        return simpleCommand(self.bot, name, self.user1, self.chat,
                             cb_reply, message)

    def store_received_string(self, recv_str: str):
        self.stored = recv_str

    def testGetStoredRut(self):
        self.setRut()

        update = self.simpleCommand('get', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        print(self.stored)
        self.assertFalse(True)

    def testGetRut(self):
        self.assertFalse(True)


class TestStart(TestCase):

    def setUp(self):
        self.tl_id = 32
        self.rut = 73829172

    def createUser(self, telegram_id, rut):
        pass

    def testProperTime(self):
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 14, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 23, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 18, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 3, 00, 00)))

        self.assertFalse(is_a_proper_time(datetime(2016, 12, 4, 14, 00)))
        self.assertFalse(is_a_proper_time(datetime(2016, 12, 3, 14, 00)))
        self.assertFalse(is_a_proper_time(datetime(2016, 12, 2, 10, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 10, 00,
                        tzinfo=pytz.timezone("America/Santiago"))))


if __name__ == '__main__':
    unittest.main()
