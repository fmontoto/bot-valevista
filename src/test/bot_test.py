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
from src.utils import is_a_proper_time
from src import model_interface
import pytz
from src.bot import update_cache_and_reply

from telegram.ext import CommandHandler, Handler, MessageHandler


class MockDispatcherOld(object):
    def __init__(self):
        self._cmd_handlers = dict()
        self._msg_handler = None
        self._error_handler = None

    def add_handler(self, handler: Handler):
        if type(handler) is MessageHandler:
            self._msg_handlers = handler
        elif type(handler) is CommandHandler:
            self._cmd_handlers[handler.command] = handler
        else:
            raise TypeError("Not supported handler.")

    def add_error_handler(self, error_handler):
        self._error_handler = error_handler

    def dispatch_cmd(cmd_name: str, msg: Optional[str]):
        pass

    def dispatch(self):
        pass


class MockDispatcher(telegram.ext.Dispatcher):
    pass


id = 0


def get_id():
    global id
    id += 1
    return id


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

    @staticmethod
    def dummyCb(*args, **kwargs):
        print("ASD")
        print(*args)
        print(*kwargs)
        return

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
        msg = telegram.Message(get_id(), from_user=self.user1,
                               date=datetime.now(), chat=self.chat,
                               text='/%s' % name,
                               reply_to_message=self.dummyCb, bot=self.bot)
        update = telegram.Update(get_id(), message=msg)
        update.message.reply_text = cb_reply
        return update

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
        self.assertEqual(self.stored, expeted)

    def testGetStoredRut(self):
        self.assertFalse(True)

    def testGetRut(self):
        self.assertFalse(True)


class TestStart(TestCase):

    def setUp(self):
        self.tl_id = 32
        self.rut = 73829172

    def createUser(self, telegram_id, rut):
        pass

    def testUpdateCacheAndReply(self):
        mock = MagicMock()
        with mock_model_interface():
            pass
            # We also need to mock the request query or "Web"
            # self.createUser(self.tl_id, self.rut)
            # update_cache_and_reply(self.tl_id, self.rut, mock, True)

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
