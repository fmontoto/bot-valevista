#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from functools import partial
import logging
from queue import Queue
import random
import os
from signal import signal, SIGINT, SIGTERM, SIGABRT
import time

from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler
from telegram.ext import Updater


from src.model_interface import User, _start, UserBadUseError
import src.utils
from src.web import ParsingException, Web

# Enable logging
try:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=log_format,
                        level=logging.DEBUG,
                        filename="log/bot.log",
                        filemode="a+")
except FileNotFoundError:
    print("log file not found")
    pass

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", None)

# Minimum hours before automatically update a cached result from a user
HOURS_TO_UPDATE = 33

RUNNING = True
SUBSCRIBED = Queue()


class ValeVistaBot(object):
    _START_MSG = (
            "Hola %s, soy el bot de los vale vista pagados por la UChile. "
            "Actualmente estoy en construcción.\n"
            "Para consultar si tienes vales vista pendientes en el banco, "
            "enviame el rut a consultar en un mensaje, por ejemplo: "
            "12.345.678-9 o 12.345.678 o 12345678.\n"
            "Si quieres que recuerde tu rut para consultarlo recurrentemente, "
            "envia: /set TU_RUT. Luego consúltalo enviando /get. \n"
            "Una vez que guardes tu rut envía /subscribe y revisaré "
            "periódicamente la página del banco para notificarte si hay "
            "nuevos vale vista."
    )
    _HELP_MSG = (
            "Estoy para ayudarte, si no sabes como utilizar o para que sirve "
            "este bot, envia /start.\n"
            "Si tienes comentarios/sugerencias/quejas abre un issue en la "
            "página de  github del proyecto: "
            "https://https://github.com/fmontoto/bot-valevista, si estas de "
            "suerte alguien se puede apiadar y ayudarte. También feliz "
            "aceptaré Pull Requests con la solución a tu problema o con una "
            "nueva funcionalidad."
    )

    _NO_RUT_MSG = ("Tu rut no está almacenado, envía '/set <RUT>' para "
                   "almacenarlo.")

    # Command handlers.
    def start(self, bot, update):
        name = (update.message.from_user.first_name or
                update.message.from_user.username)
        update.message.reply_text(self._START_MSG % name)

    def help(self, bot, update):
        update.message.reply_text(self._HELP_MSG)

    def get_rut(self, bot, update):
        telegram_id = update.message.from_user.id
        logger.info("Get %s", telegram_id)
        rut_ = User.get_rut(telegram_id)
        if rut_:
            return update_cache_and_reply(telegram_id, rut_,
                                          update.message.reply_text, False)
        update.message.reply_text(self._NO_RUT_MSG)

    def set_rut(self, bot, update):
        spl = update.message.text.split(' ')
        if len(spl) < 2:
            update.message.reply_text(
                    "Especifica el rut para poder guardarlo.")
        rut = normalize_rut(spl[1])

        if not normalize_rut(spl[1]):
            update.message.reply_text("Rut no valido.")
            return
        User.set_rut(update.message.from_user.id, normalize_rut(spl[1]))
        logger.info("User %s set rut %s", update.message.from_user.id,
                    normalize_rut(spl[1]))
        update.message.reply_text(
            ("Rut:%s-%s guardado correctamente\n Envía /get para consultar "
             "directamente" % (rut, digito_verificador(rut))))

    def subscribe(self, bot, update):
        try:
            User.subscribe(update.message.from_user.id, update.message.chat.id)
        except UserBadUseError as e:
            logger.warning(e.public_message)
            update.message.reply_text(e.public_message)
        else:
            logger.info("User %s subscribed", update.message.from_user.id)
            update.message.reply_text(
                ("Estas subscrito, si hay cambios con respecto al último "
                 "resultado que miraste aquí, te enviaré un mensaje. Estaré "
                 "revisando la página del banco cada uno o dos días. Si la "
                 "desesperación es mucha, recuerda que puedes preguntarme con "
                 "/get \n Para eliminar tu subscripción, envía el comando "
                 "/unsubscribe."))

    def unsubscribe(self, bot, update):
        try:
            User.unsubscribe(update.message.from_user.id,
                             update.message.chat.id)
        except UserBadUseError as e:
            logger.warning(e.public_message)
            update.message.reply_text(e.public_message)
        else:
            logger.info("User %s unsubscribed", update.message.from_user.id)
            update.message.reply_text(("Ya no estás subscrito, para volver a "
                                       "estarlo, envía /subscribe"))

    def debug(self, bot, update):
        logger.info("Debug: %s, %s" % (bot, update))

    def error(self, bot, update, error):
        logger.warn("Update %s caused error %s" % (update, error))

    # Non command messages
    def msg(self, bot, update):
        # Log every msg received.
        logger.info("MSG:[%s]", update.message.text)
        is_rut = normalize_rut(update.message.text)
        if not is_rut:
            echo(bot, update)
        else:
            update_cache_and_reply(update.message.from_user.id, is_rut,
                                   update.message.reply_text, False)

    # Non telegram handlers.
    def echo(self, bot, update):
        update.message.reply_text(update.message.text)


def update_cache_and_reply(telegram_id, rut, reply_fn,
                           reply_only_on_change_and_expected):
    try:
        web_parser = Web(rut, digito_verificador(rut))
        response, changed = web_parser.get_parsed_results(telegram_id)
    except ParsingException as e:
        reply_fn(e.public_message)
    except Exception as e:
        logger.error(e)
        reply_fn(("Ups!, un error inesperado ha ocurrido, "
                  "lo solucionaremos a la brevedad (?)"))
    else:
        if not reply_only_on_change_and_expected:
            reply_fn(response)
            return
        if web_parser.page_type == web_parser.EXPECTED and changed:
            reply_fn(response)


def signal_handler(signum, frame):
    global RUNNING
    if RUNNING:
        RUNNING = False
    else:
        logger.warn("Exiting now!")
        os.exit(1)


def step(updater, hours=HOURS_TO_UPDATE):
    users_to_update = User.get_subscriber_not_retrieved_hours_ago(hours)
    logger.info("To update queue length: %s", len(users_to_update))
    if len(users_to_update) > 0:
        user_to_update = users_to_update[random.randint(
                0, len(users_to_update) - 1)]
        update_cache_and_reply(
                user_to_update.telegram_id, user_to_update.rut,
                partial(updater.bot.sendMessage,
                        User.get_chat_id(user_to_update.id)), True)


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
