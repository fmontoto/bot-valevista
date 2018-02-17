#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum
import datetime
from functools import partial
import logging
import logging.handlers
from queue import Queue
import random
import os
from signal import signal, SIGINT, SIGTERM, SIGABRT
import time
from typing import Text

from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler
from telegram.ext import Updater
import telegram


from src.messages import Messages
from src.model_interface import User, _start
from src.model_interface import UserBadUseError, UserDoesNotExistError
from src import model_interface
from src.utils import Rut
import src.utils
from src import web
from src.web import ParsingException, Web, WebRetriever

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Rotating file handler, rotates every 4 mondays.
try:
    _log_handler = logging.handlers.TimedRotatingFileHandler(
            'log/bot.log', when='W0', interval=4,
            utc=True)  # type: logging.Handler
    _log_handler.setLevel(logging.DEBUG)
except FileNotFoundError:
    print('log dir not found for file logging')
    _log_handler = logging.StreamHandler()
    _log_handler.setLevel(logging.DEBUG)

_log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_log_handler.setFormatter(logging.Formatter(_log_format))
logger.addHandler(_log_handler)

logger.info('Logging started')


TOKEN = os.getenv("BOT_TOKEN", None)

# Minimum hours before automatically update a cached result from a user
HOURS_TO_UPDATE = 33

RUNNING = True
SUBSCRIBED: Queue = Queue()


class ValeVistaBot(object):
    # Arguments are dependency injection for test purposes.
    def __init__(self, web_retriever: WebRetriever=None,
                 cache: model_interface.Cache=None) -> None:
        if web_retriever is None:
            self._web_retriever = web.WebPageDownloader()  # type: WebRetriever
        else:
            self._web_retriever = web_retriever
        self._cache = cache or model_interface.Cache()

    # Command handlers.
    def start(self, bot, update: telegram.Update):
        name = (update.message.from_user.first_name or
                update.message.from_user.username)
        update.message.reply_text(Messages.START_MSG % name)

    # Sends a help message to the user.
    def help(self, bot, update: telegram.Update):
        update.message.reply_text(Messages.HELP_MSG)

    # Query the service using the stored rut.
    def get_rut(self, bot, update: telegram.Update):
        telegram_id = update.message.from_user.id
        logger.info("Get %s", telegram_id)
        rut_ = User.get_rut(telegram_id)
        if rut_:
            return self.query_the_bank_and_reply(telegram_id, rut_,
                                                 update.message.reply_text,
                                                 self.ReplyWhen.ALWAYS)
        update.message.reply_text(Messages.NO_RUT_MSG)

    def set_rut(self, bot, update: telegram.Update):
        spl = update.message.text.split(' ')
        if len(spl) < 2:
            update.message.reply_text(Messages.SET_EMPTY_RUT)

        rut = Rut.build_rut(spl[1])

        if rut is None:
            update.message.reply_text(Messages.SET_INVALID_RUT)
            return

        User.set_rut(update.message.from_user.id, rut)

        logger.info("User %s set rut %s", update.message.from_user.id,
                    Rut._normalize_rut(spl[1]))
        update.message.reply_text(Messages.SET_RUT % rut)

    def subscribe(self, bot, update: telegram.Update):
        try:
            User.subscribe(update.message.from_user.id, update.message.chat.id)
        except UserBadUseError as e:
            logger.warning(e.public_message)
            update.message.reply_text(e.public_message)
        else:
            logger.info("User %s subscribed", update.message.from_user.id)
            update.message.reply_text(Messages.SUBSCRIBED)

    def unsubscribe(self, bot, update: telegram.Update):
        try:
            User.unsubscribe(update.message.from_user.id,
                             update.message.chat.id)
        except UserBadUseError as e:
            logger.warning(e.public_message)
            update.message.reply_text(e.public_message)
        except UserDoesNotExistError as e:
            logger.warning(e.public_message)
            update.message.reply_text(Messages.UNSUBSCRIBE_NON_SUBSCRIBED)
        else:
            logger.info("User %s unsubscribed", update.message.from_user.id)
            update.message.reply_text(Messages.UNSUBSCRIBED)

    def debug(self, bot, update: telegram.Update):
        logger.info("Debug: %s, %s" % (bot, update))

    def error(self, bot, update: telegram.Update, error):
        logger.warn("Update %s caused error %s" % (update, error))

    # Non command messages
    def msg(self, bot, update: telegram.Update):
        # Log every msg received.
        logger.info("MSG:[%s]", update.message.text)
        rut = Rut.build_rut(update.message.text)
        if rut:
            self.echo(bot, update)
        else:
            self.query_the_bank_and_reply(update.message.from_user.id, rut,
                                          update.message.reply_text,
                                          self.ReplyWhen.ALWAYS)

    # Non telegram handlers.
    def echo(self, bot, update):
        update.message.reply_text(update.message.text)

    class ReplyWhen(enum.Enum):
        ALWAYS = 1
        IS_USEFUL_FOR_USER = 2

    def query_the_bank_and_reply(self, telegram_id: int, rut: Rut, reply_fn,
                                 reply_when: ReplyWhen):
        try:
            web_result = Web(rut, telegram_id, self._web_retriever,
                             self._cache)
            response = web_result.get_results()
        # Expected exception.
        except ParsingException as e:
            if reply_when == self.ReplyWhen.ALWAYS:
                reply_fn(e.public_message)
            return
        except Exception as e:
            logger.exception("Error:")
            if reply_when == self.ReplyWhen.ALWAYS:
                reply_fn(Messages.INTERNAL_ERROR)
            return

        if reply_when == self.ReplyWhen.ALWAYS:
            reply_fn(response)
        elif reply_when == self.ReplyWhen.IS_USEFUL_FOR_USER:
            if web_result.is_useful_info_for_user():
                reply_fn(response)
        else:
            logger.error('Not handled enum: %s', reply_when)


def signal_handler(signum, frame):
    global RUNNING
    if RUNNING:
        RUNNING = False
    else:
        logger.error("Exiting now!")
        os.exit(1)


def step(updater, hours=HOURS_TO_UPDATE):
    users_to_update = User.get_subscriber_not_retrieved_hours_ago(hours)
    logger.debug("To update queue length: %s", len(users_to_update))
    if len(users_to_update) > 0:
        user_to_update = users_to_update[random.randint(
                0, len(users_to_update) - 1)]
        self.query_the_bank_and_reply(
                user_to_update.telegram_id, user_to_update.rut,
                partial(updater.bot.sendMessage,
                        User.get_chat_id(user_to_update.id)),
                self.ReplyWhen.IS_USEFUL_FOR_USER)


def loop(updater):
    stop_signals = (SIGINT, SIGTERM, SIGABRT)
    for sig in stop_signals:
        signal(sig, signal_handler)

    while RUNNING:
        if utils.is_a_proper_time(datetime.datetime.utcnow()):
            step(updater)
        time.sleep(random.randint(5 * 60, 25 * 60))  # Between 5 and 25 minutes
    updater.stop()


def add_handlers(dispatcher: Dispatcher, bot: ValeVistaBot) -> None:
    dispatcher.add_handler(CommandHandler("start", bot.start))
    dispatcher.add_handler(CommandHandler("set", bot.set_rut))
    dispatcher.add_handler(CommandHandler("get", bot.get_rut))
    dispatcher.add_handler(CommandHandler("debug", bot.debug))
    dispatcher.add_handler(CommandHandler("help", bot.help))
    dispatcher.add_handler(CommandHandler("subscribe", bot.subscribe))
    dispatcher.add_handler(CommandHandler("unsubscribe", bot.unsubscribe))
    dispatcher.add_handler(MessageHandler(Filters.text, bot.msg))
    dispatcher.add_error_handler(bot.error)


def main():
    # Start the db
    _start()
    bot = ValeVistaBot()

    updater = Updater(TOKEN)

    dp = updater.dispatcher

    add_handlers(dp, bot)

    updater.start_webhook(listen="0.0.0.0", port=443,
                          url_path="/bot-valevista")
    loop(updater)


if __name__ == "__main__":
    main()
