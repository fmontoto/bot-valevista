import datetime
from typing import Optional
import unittest
from unittest import TestCase
from unittest.mock import MagicMock
import telegram
import queue
from concurrent.futures import ThreadPoolExecutor

from src.test.model_interface_test import mock_model_interface, User
from src.bot import ValeVistaBot
from src.bot import add_handlers
from src import bot
from src.utils import is_a_proper_time, Rut
from src import model_interface
from src.messages import Messages
from src.test import web_test
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
                           date=datetime.datetime.now(), chat=chat,
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
                               date=datetime.datetime.now(), chat=self.chat,
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
        expected = Messages.HELP_MSG
        update = self.simpleCommand('help',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testGetNoRutSet(self):
        expected = Messages.NO_RUT_MSG
        update = self.simpleCommand('get', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetEmptyRut(self):
        expected = Messages.SET_EMPTY_RUT
        update = self.simpleCommand('set', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetInvalidRut(self):
        expected = Messages.SET_INVALID_RUT
        update = self.simpleCommand('set NO_VALID_RUT',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)

    def testSetRut(self):
        expected = Messages.SET_RUT % str(self.rut)
        update = self.simpleCommand('set %s' % self.rut_non_std_str,
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(self.stored, expected)


class TestFunctionalBot(TestCase):
    _EXPECTED_ON_SUCCESS = (
            "Fecha de Pago: 28/10/2016\n"
            "Medio de Pago: Abono en Cuenta Corriente de Otros Bancos\n"
            "Oficina/Banco: BCO. CRED. E INVERSIONES\n"
            "Estado: Pagado / Rendido\n"
            "\n"
            "Fecha de Pago: 30/09/2016\n"
            "Medio de Pago: Abono en Cuenta Corriente de Otros Bancos\n"
            "Oficina/Banco: BCO. CRED. E INVERSIONES\n"
            "Estado: Pagado / Rendido\n"
            "\n"
            "Fecha de Pago: 31/08/2016\n"
            "Medio de Pago: Abono en Cuenta Corriente de Otros Bancos\n"
            "Oficina/Banco: BCO. CRED. E INVERSIONES\n"
            "Estado: Pagado / Rendido"
    )

    def setUp(self):
        model_interface._start(True)
        self.retriever = web_test.WebPageFromFileRetriever()
        self.bot = ValeVistaBot(self.retriever)
        self.queue = queue.Queue()
        self.dispatcher = MockDispatcher(self.bot, self.queue)
        self.user1_telegram_id = get_id()
        self.user1 = telegram.User(id=self.user1_telegram_id,
                                   first_name='john', username='ujohn',
                                   is_bot=False)
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

    def testGetRut(self):
        expected = Messages.NO_RUT_MSG
        update = self.simpleCommand('get', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSubscribeNoRut(self):
        expected = Messages.SUBSCRIBE_NO_RUT
        update = self.simpleCommand('subscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSubscribe(self):
        self.setRut()
        expected = Messages.SUBSCRIBED
        update = self.simpleCommand('subscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSubscribeTwice(self):
        self.setRut()
        expected = Messages.ALREADY_SUBSCRIBED
        update = self.simpleCommand('subscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        update = self.simpleCommand('subscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testUnsubscribe(self):
        expected = Messages.UNSUBSCRIBE_NON_SUBSCRIBED
        update = self.simpleCommand('unsubscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSetRutUnsubscribe(self):
        self.setRut()
        expected = Messages.UNSUBSCRIBE_NON_SUBSCRIBED
        update = self.simpleCommand('unsubscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSubscribeUnsubscribe(self):
        self.setRut()
        expected = Messages.UNSUBSCRIBED
        update = self.simpleCommand('subscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)

        update = self.simpleCommand('unsubscribe',
                                    cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    # Test getting results.
    def testGetStoredRut(self):
        expected = self._EXPECTED_ON_SUCCESS
        self.setRut()
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('pagado_rendido.html'))
        update = self.simpleCommand('get', cb_reply=self.store_received_string)
        self.dispatcher.process_update(update)
        self.assertEqual(expected, self.stored)

    def testSimpleQueryTheBankAndReply(self):
        expected = self._EXPECTED_ON_SUCCESS
        # This enrolls the user.
        self.setRut()
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('pagado_rendido.html'))
        self.bot.query_the_bank_and_reply(self.user1_telegram_id, self.rut,
                                          self.store_received_string,
                                          ValeVistaBot.ReplyWhen.ALWAYS)
        self.assertEqual(expected, self.stored)

    def testQueryTheBankAndReply(self):
        expected = self._EXPECTED_ON_SUCCESS
        # This enrolls the user.
        self.setRut()
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('pagado_rendido.html'))
        self.bot.query_the_bank_and_reply(self.user1_telegram_id, self.rut,
                                          self.store_received_string,
                                          ValeVistaBot.ReplyWhen.IS_USEFUL_FOR_USER)
        self.assertEqual(expected, self.stored)

    def testQueryTheBankAndReplyCache(self):
        # This enrolls the user.
        self.setRut()
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('pagado_rendido.html'))
        self.bot.query_the_bank_and_reply(self.user1_telegram_id, self.rut,
                                          self.store_received_string,
                                          ValeVistaBot.ReplyWhen.ALWAYS)
        self.assertEqual(self._EXPECTED_ON_SUCCESS, self.stored)
        self.stored = None
        self.bot.query_the_bank_and_reply(
                self.user1_telegram_id, self.rut, self.store_received_string,
                ValeVistaBot.ReplyWhen.IS_USEFUL_FOR_USER)
        self.assertEqual(None, self.stored)
        self.bot.query_the_bank_and_reply(self.user1_telegram_id, self.rut,
                                          self.store_received_string,
                                          ValeVistaBot.ReplyWhen.ALWAYS)
        self.assertEqual(self._EXPECTED_ON_SUCCESS, self.stored)

    def testQueryTheBankAndReply(self):
        expected = self._EXPECTED_ON_SUCCESS
        # Inmediate time of expiration for cache.
        cache = model_interface.Cache(datetime.timedelta(0))
        bot = ValeVistaBot(self.retriever, cache)
        # This enrolls the user.
        self.setRut()
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('pagado_rendido.html'))
        bot.query_the_bank_and_reply(self.user1_telegram_id, self.rut,
                                          self.store_received_string,
                                          ValeVistaBot.ReplyWhen.ALWAYS)
        self.assertEqual(self._EXPECTED_ON_SUCCESS, self.stored)
        self.retriever.setPath(
                web_test.TestFilesBasePath().joinpath('cliente.html'))
        import pdb; pdb.set_trace()
        bot.query_the_bank_and_reply(
                self.user1_telegram_id, self.rut, self.store_received_string,
                ValeVistaBot.ReplyWhen.ALWAYS)
        self.assertEqual(Messages.CLIENTE_ERROR, self.stored)


class TestStart(TestCase):

    def setUp(self):
        self.tl_id = 32
        self.rut = 73829172

    def createUser(self, telegram_id, rut):
        pass

    def testProperTime(self):
        self.assertTrue(
                is_a_proper_time(datetime.datetime(2016, 12, 2, 14, 00)))
        self.assertTrue(
                is_a_proper_time(datetime.datetime(2016, 12, 2, 23, 00)))
        self.assertTrue(
                is_a_proper_time(datetime.datetime(2016, 12, 2, 18, 00)))
        self.assertTrue(
                is_a_proper_time(datetime.datetime(2016, 12, 3, 00, 00)))

        self.assertFalse(
                is_a_proper_time(datetime.datetime(2016, 12, 4, 14, 00)))
        self.assertFalse(
                is_a_proper_time(datetime.datetime(2016, 12, 3, 14, 00)))
        self.assertFalse
        (is_a_proper_time(datetime.datetime(2016, 12, 2, 10, 00)))
        self.assertTrue(is_a_proper_time(datetime.datetime(2016, 12, 2, 10, 00,
                        tzinfo=pytz.timezone("America/Santiago"))))


if __name__ == '__main__':
    unittest.main()
