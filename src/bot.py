#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from queue import Queue
import os
from signal import signal, SIGINT, SIGTERM, SIGABRT
import time

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from src.utils import digito_verificador, normalize_rut
from src.web import ParsingException, Web
from src.model_interface import User, CachedResult

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    filename="log/bot.log",
                    filemode="a+")

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", None)

RUNNING = True
SUBSCRIBED = Queue()

def start(bot, update):
    name = update.message.from_user.first_name or update.message.from_user.username
    msg = ("Hola %s, soy el bot de los vale vista pagados por la UChile. Actualmente estoy en construcción.\n"
	       "Para consultar si tienes vales vista pendientes en el banco, enviame el rut a consultar en un mensaje, "
           "por ejemplo: 12.345.678-9.\n"
           "Si quieres que recuerde tu rut para consultarlo recurrentemente, envia: /set TU_RUT. "
           "Luego consultalo enviando /get.")
    update.message.reply_text(msg % name)

def help(bot, update):
    update.message.reply_text(("Estoy para ayudarte, si no sabes como utilizar o para que sirve este bot, "
                               "envia /start.\n"
                               "Si tienes comentarios/sugerencias/quejas abre un issue en el github del proyecto: "
                               "https://https://github.com/fmontoto/bot-valevista, si estas de suerte alguien se "
                               "puede apiadar y ayudarte. De lo contrario puedes enviar un Pull Request con lo que "
                               "solucione el problema o con una nueva funcionalidad."))

def msg(bot, update):
    logger.info("MSG:[%s]", update.message.text)
    is_rut = normalize_rut(update.message.text)
    if not is_rut:
        echo(bot, update)
    else:
        rut(bot, update, is_rut)

def echo(bot, update):
    update.message.reply_text(update.message.text)

def set_rut(bot, update):
    spl = update.message.text.split(' ')
    if len(spl) < 2:
        update.message.reply_text("Especifica el rut para poder guardarlo.")
    rut = normalize_rut(spl[1])

    if not normalize_rut(spl[1]):
        update.message.reply_text("Rut no valido.")
        return
    User.set_rut(update.message.from_user.id, normalize_rut(spl[1]))
    update.message.reply_text("Rut:%s-%s guardado correctamente" % (rut, digito_verificador(rut)))

def get_by_rut(bot, update):
    rut_ = User.get_rut(update.message.from_user.id)
    if rut_:
        return rut(bot, update, rut_)
    update.message.reply_text("No hay un rut almacenado, utiliza '/set <RUT>' para almacenarlo.")

def rut(bot, update, rut):
    try:
        response = Web(rut, digito_verificador(rut)).get_parsed_results(update.message.from_user.id)
    except ParsingException as e:
        update.message.reply_text(e.public_message)
    except Exception as e:
        logger.error(e)
        update.message.reply_text("ups, un error ha ocurrido =( lo solucionaremos a la brevedad (?)")
    else:
        update.message.reply_text(response)

def subscribe(bot, update):
    SUBSCRIBED.put_nowait(update.message.chat.id)
    update.message.reply_text("Ok!")

def debug(bot, update):
    logger.info("Debug: %s, %s" % (bot, update))

def error(bot, update, error):
    logger.warn("Update %s caused error %s" % (update, error))

def signal_handler(self, signum, frame):
    global RUNNING
    if RUNNING:
        RUNNING = False
    else:
        logger.warn("Exiting now!")
        os.exit(1)

def loop(updater):
    stop_signals = (SIGINT, SIGTERM, SIGABRT)
    for sig in stop_signals:
        signal(sig, signal_handler)

    while RUNNING:
        if not SUBSCRIBED.empty():
            chat_id = SUBSCRIBED.get_nowait()
            updater.bot.sendMessage(chat_id, "Testing not reply ms!")
        time.sleep(3)
    updater.stop()

def main():
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("set", set_rut))
    dp.add_handler(CommandHandler("get", get_by_rut))
    dp.add_handler(CommandHandler("debug", debug))
    dp.add_handler(CommandHandler("help", help))

    dp.add_handler(CommandHandler("subscribe"), subscribe)

    dp.add_handler(MessageHandler(Filters.text, msg))

    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0", port=443, url_path="/bot-valevista")
    loop(updater)

if __name__ == "__main__":
    main()
