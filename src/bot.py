#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Module implementing the main loop and the telegram API."""

import enum
import datetime
from functools import partial
import logging
import logging.handlers
from queue import Queue
import random
import os
from signal import signal, SIGINT, SIGTERM, SIGABRT
import sys
import time

from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler
from telegram.ext import Updater
import telegram


from src.messages import Messages
from src.model_interface import User, DbConnection
from src.model_interface import UserBadUseError, UserDoesNotExistError
from src import model_interface
from src.utils import Rut
from src import utils
from src import web
from src.web import ParsingException, Web, WebRetriever

logger = logging.getLogger('bot_main_logger')  # pylint: disable=invalid-name
logger.setLevel(logging.DEBUG)

# Rotating file handler, rotates every 4 mondays.
try:
    _LOG_HANDLER = logging.handlers.TimedRotatingFileHandler(
            'log/bot.log', when='W0', interval=4,
            utc=True)  # type: logging.Handler
    _LOG_HANDLER.setLevel(logging.DEBUG)
except FileNotFoundError:
    print('log dir not found for file logging')
    _LOG_HANDLER = logging.StreamHandler()
    _LOG_HANDLER.setLevel(logging.DEBUG)

_LOG_FORMAT = (
        "%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(levelname)s "
        "- %(message)s")
_LOG_HANDLER.setFormatter(logging.Formatter(_LOG_FORMAT))
logger.addHandler(_LOG_HANDLER)
logger.info('Logging started')


# Gets the bot token from the environment.
TOKEN = os.getenv("BOT_TOKEN", None)

# Minimum hours before automatically update a cached result from a user
HOURS_TO_UPDATE = 33

SUBSCRIBED = Queue()  # type: Queue


class ValeVistaBot():
    """Class with all the telegram handlers for the bot."""
    # Testing purposes.
    username = "valevistabot"

    # Arguments are dependency injection for test purposes.
    def __init__(self, db_connection: DbConnection,
                 web_retriever: WebRetriever = None,
                 cache: model_interface.Cache = None) -> None:
        if web_retriever is None:
            self._web_retriever = web.WebPageDownloader()  # type: WebRetriever
        else:
            self._web_retriever = web_retriever
        self._cache = cache or model_interface.Cache(db_connection)
        self._running = True
        self._db_connection = db_connection

    # Command handlers.
    @staticmethod
    def start(unused_bot, update: telegram.Update):
        """Prints the start message."""
        logger.debug('USR[%s]; START', update.message.from_user.id)
        name = (update.message.from_user.first_name or
                update.message.from_user.username)
        update.message.reply_text(Messages.START_MSG % name)

    # Sends a help message to the user.
    @staticmethod
    def help(unused_bot, update: telegram.Update):
        """Prints help message."""
        logger.debug('USR[%s]; HELP', update.message.from_user.id)
        update.message.reply_text(Messages.HELP_MSG)

    # Query the service using the stored rut.
    def get_rut(self, unused_bot, update: telegram.Update):
        """Query info for a previously set rut."""
        telegram_id = update.message.from_user.id
        rut = User(self._db_connection).get_rut(telegram_id)
        if rut:
            logger.debug('USR[%s]; GET_RUT[%s]', telegram_id, rut)
            self.query_the_bank_and_reply(telegram_id, rut,
                                          update.message.reply_text,
                                          self.ReplyWhen.ALWAYS)
            return
        logger.debug('USR[%s]; GET_NO_RUT', telegram_id)
        update.message.reply_text(Messages.NO_RUT_MSG)

    def set_rut(self, unused_bot, update: telegram.Update):
        """Set a rut to easily query it in the future."""
        spl = update.message.text.split(' ')
        if len(spl) < 2:
            logger.debug('USR[%s]; EMPTY_RUT', update.message.from_user.id)
            update.message.reply_text(Messages.SET_EMPTY_RUT)
            return

        rut = Rut.build_rut(spl[1])

        if rut is None:
            logger.debug('USR[%s]; INVALID_RUT', update.message.from_user.id)
            update.message.reply_text(Messages.SET_INVALID_RUT)
            return

        User(self._db_connection).set_rut(update.message.from_user.id, rut)

        logger.debug("USR[%s]; SET_RUT[%s]", update.message.from_user.id, rut)
        update.message.reply_text(Messages.SET_RUT % rut)

    def subscribe(self, unused_bot, update: telegram.Update):
        """Subscribe and get updates on valevista changes for your rut."""
        logger.debug("USR:[%s]; SUBSC", update.message.from_user.id)
        chat_type = update.message.chat.type
        if chat_type != 'private':
            logger.debug('USR[%s]; FROM NON PRIVATE CHAT[%s]',
                         update.message.from_user.id, chat_type)
            update.message.reply_text(Messages.FROM_NON_PRIVATE_CHAT)
            return
        try:
            User(self._db_connection).subscribe(
                    update.message.from_user.id, update.message.chat.id)
        except UserBadUseError as bad_user_exep:
            logger.warning(bad_user_exep.public_message)
            update.message.reply_text(bad_user_exep.public_message)
        else:
            update.message.reply_text(Messages.SUBSCRIBED)

    def unsubscribe(self, unused_bot, update: telegram.Update):
        """Stop getting updates."""
        logger.debug("USR:[%s]; UNSUBSC", update.message.from_user.id)
        try:
            User(self._db_connection).unsubscribe(update.message.from_user.id,
                                                  update.message.chat.id)
        except UserBadUseError as bad_user_exep:
            logger.warning(bad_user_exep.public_message)
            update.message.reply_text(bad_user_exep.public_message)
        except UserDoesNotExistError as user_exep:
            logger.warning(user_exep.public_message)
            update.message.reply_text(Messages.UNSUBSCRIBE_NON_SUBSCRIBED)
        else:
            logger.info("User %s unsubscribed", update.message.from_user.id)
            update.message.reply_text(Messages.UNSUBSCRIBED)

    @staticmethod
    def debug(bot, update: telegram.Update):
        """Telegram framework debug handler."""
        logger.info("Debug: %s, %s", bot, update)

    @staticmethod
    def error(unused_bot, update: telegram.Update, error):
        """Telegram framework error handler."""
        logger.warning("Update %s caused error: %s", update, error)

    # Non command messages
    def msg(self, bot, update: telegram.Update):
        """Handler when a message arrives."""
        # Log every msg received.
        logger.debug("USR:[%s]; MSG:[%s]", update.message.from_user.id,
                     update.message.text)
        rut = Rut.build_rut(update.message.text)
        if rut:
            self.query_the_bank_and_reply(update.message.from_user.id, rut,
                                          update.message.reply_text,
                                          self.ReplyWhen.ALWAYS)
        elif Rut.looks_like_rut(update.message.text):
            update.message.reply_text(Messages.LOOKS_LIKE_RUT)
        else:
            self.echo(bot, update)

    # Non telegram handlers.
    @staticmethod
    def echo(unused_bot, update):
        """Replies with the message received."""
        update.message.reply_text(update.message.text)

    @staticmethod
    def send_message_retry(send_fx, retries):
        """Calls send_fx and it retries if it fails due network issues. """

        while True:
            try:
                send_fx()
            except telegram.error.NetworkError:
                if retries == 0:
                    logger.exception("Network error, retrying...")
                    break
                else:
                    retries = retries - 1
                    logger.warning("Network error, retrying.")
            break

    class ReplyWhen(enum.Enum):
        """When to send a message to the user."""
        ALWAYS = 1  # Send a message even if not useful data is found.
        IS_USEFUL_FOR_USER = 2  # Only send a message if there is useful data.

    def query_the_bank_and_reply(self, telegram_id: int, rut: Rut, reply_fn,
                                 reply_when: ReplyWhen):
        """Query the bank for updates, and send a message to the user.

        If reply_when is set to always, send a message to the user even if
        there are no changes from the last time we queried. Otherwise will
        send a message to the user only if new and useful information was
        retrieved.
        """
        def reply(msg):
            """Wrapper for retrying on network error."""
            return self.send_message_retry(lambda: reply_fn(msg), 3)
        try:
            web_result = Web(self._db_connection, rut, telegram_id,
                             self._cache, self._web_retriever)
            response = web_result.get_results()
        # Expected exception.
        except ParsingException as parsing_exep:
            if reply_when == self.ReplyWhen.ALWAYS:
                reply(parsing_exep.public_message)
            return
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error:")
            if reply_when == self.ReplyWhen.ALWAYS:
                reply(Messages.INTERNAL_ERROR)
            return

        if reply_when == self.ReplyWhen.ALWAYS:
            reply(response)
        elif reply_when == self.ReplyWhen.IS_USEFUL_FOR_USER:
            if web_result.is_useful_info_for_user():
                logger.debug('USR[%s]; Useful[%s]', telegram_id, response)
                reply(response)
        else:
            logger.error('Not handled enum: %s', reply_when)

    # Bot helping functions.
    def add_handlers(self, dispatcher: Dispatcher) -> None:
        """Adds all ValeVistaBot handlers to 'dispatcher'."""
        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(CommandHandler("set", self.set_rut))
        dispatcher.add_handler(CommandHandler("get", self.get_rut))
        dispatcher.add_handler(CommandHandler("debug", self.debug))
        dispatcher.add_handler(CommandHandler("help", self.help))
        dispatcher.add_handler(CommandHandler("subscribe", self.subscribe))
        dispatcher.add_handler(CommandHandler("unsubscribe", self.unsubscribe))
        dispatcher.add_handler(MessageHandler(Filters.text, self.msg))
        dispatcher.add_error_handler(self.error)

    def signal_handler(self, unused_signum, unused_frame):
        """Gracefully stops the bot on a received signal."""
        if self._running:
            self._running = False
        else:
            logger.error("Exiting now!")
            sys.exit(1)

    def step(self, updater, hours=HOURS_TO_UPDATE):
        """Checks the bank for subscribed users.

        If useful new data is available, send a message to the user.
        """
        user_conn = User(self._db_connection)
        users_to_update = user_conn.get_subscribers_to_update(hours)
        if not users_to_update:
            return

        user_to_update = users_to_update[random.randint(
                0, len(users_to_update) - 1)]
        logger.debug("To update queue length: %s. Updating: user_id=%s",
                     len(users_to_update), user_to_update.id)
        rut = Rut.build_rut_sin_digito(user_to_update.rut)
        user_chat_id = user_conn.get_chat_id(user_to_update.id)
        try:
            self.query_the_bank_and_reply(
                    user_to_update.telegram_id, rut,
                    partial(updater.bot.sendMessage, user_chat_id),
                    ValeVistaBot.ReplyWhen.IS_USEFUL_FOR_USER)
        except telegram.error.Unauthorized:
            logger.debug(
                    'USR[%s]; CHAT_ID[%s] Unauthorized us, unsubscribing...',
                    user_to_update.telegram_id, user_chat_id)
            user_conn.unsubscribe(user_to_update.telegram_id, user_chat_id)

    def loop(self, updater):
        """Background loop to check for updates."""

        while self._running:
            try:
                if utils.is_a_proper_time(datetime.datetime.utcnow()):
                    self.step(updater)
            except Exception:  # pylint: disable=broad-except
                logger.exception("step failed")
            # Between 5 and 25 minutes
            time.sleep(random.randint(5 * 60, 25 * 60))
        updater.stop()


def main():
    """Entry point."""

    bot = ValeVistaBot(DbConnection())

    stop_signals = (SIGINT, SIGTERM, SIGABRT)
    for sig in stop_signals:
        signal(sig, bot.signal_handler)

    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    bot.add_handlers(dispatcher)

    updater.start_webhook(listen="0.0.0.0", port=443,
                          url_path="/bot-valevista")
    bot.loop(updater)


if __name__ == "__main__":
    main()
