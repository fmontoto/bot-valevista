#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .utils import digito_verificador, normalize_rut
from .web import ParsingException, Web
from .model_interface import get_user_rut, set_user_rut

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    filename="log/bot.log",
                    filemode="a+")

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", None)

def start(bot, update):
    name = update.message.from_user.first_name or update.message.from_user.username
    msg = ("Hola %s, soy el bot de los vale vista pagados por la UChile. Actualmente estoy en construcción.\n"
	   "Para consultar si tienes vales vista pendientes en el banco, enviame tu rut en un mensaje: <12.345.678=9>")
    update.message.reply_text(msg % name)

def help(bot, update):
    update.message.reply_text(("Estoy para ayudarte, si no sabes como utilizar este bot, envia /start. "
			       "Si tienes comentarios/sugerencias/quejas escribele a mi creador: fmontotomonroy@gmail.com"
			       ", cuando tenga tiempo quizas te responda, o quizás no, a mi me dejo a medio terminar =("))

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
    set_user_rut(update.message.from_user.id, normalize_rut(spl[1]))
    update.message.reply_text("Rut:%s-%s guardado correctamente" % (rut, digito_verificador(rut)))

def get_by_rut(bot, update):
    rut_ = get_user_rut(update.message.from_user.id)
    if normalize_rut(rut_):
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

def debug(bot, update):
    logger.info("Debug: %s, %s" % (bot, update))

def error(bot, update, error):
    logger.warn("Update %s caused error %s" % (update, error))

def main():
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("set", set_rut))
    dp.add_handler(CommandHandler("get", get_by_rut))
    dp.add_handler(CommandHandler("debug", debug))
    dp.add_handler(CommandHandler("help", help))

    dp.add_handler(MessageHandler(Filters.text, msg))

    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0", port=443, url_path="/bot-valevista")
    updater.idle()

if __name__ == "__main__":
    main()
