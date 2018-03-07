"""Static messages sent by the bot."""


# pylint: disable=too-few-public-methods
class Messages(object):
    """Class to hold most static messages the bot sends to the user."""
    # ####################################### #
    # ###### Command success message. ####### #
    # ####################################### #
    # On start command.
    START_MSG = (
            "Hola %s, soy el bot de los vale vista pagados por la UChile. "
            "Actualmente estoy en construcción.\n"
            "Para consultar si tienes vales vista pendientes en el banco, "
            "enviame el rut a consultar en un mensaje, por ejemplo: "
            "12.345.678-9, los puntos son opcionales, pero debes especificar "
            "el dígito verificador separado con un guión.\n"
            "Si quieres que recuerde tu rut para consultarlo recurrentemente, "
            "envia: /set TU_RUT. Luego consúltalo enviando /get. \n"
            "Una vez que guardes tu rut envía /subscribe y revisaré "
            "periódicamente la página del banco para notificarte si hay "
            "nuevos vale vista."
    )

    # On help command.
    HELP_MSG = (
            "Estoy para ayudarte, si no sabes como utilizar o para que sirve "
            "este bot, envia /start.\n"
            "Si tienes comentarios/sugerencias/quejas abre un issue en la "
            "página de  github del proyecto: "
            "https://https://github.com/fmontoto/bot-valevista, si estas de "
            "suerte alguien se puede apiadar y ayudarte. También le puedes "
            "hablar directamente a mi creador: @fmontoto"
    )

    SUBSCRIBED = (
            "Estas subscrito, si hay cambios con respecto al último resultado "
            "que miraste aquí, te enviaré un mensaje. Estaré revisando la "
            "página del banco cada uno o dos días. Si la desesperación es "
            "mucha, recuerda que puedes preguntarme con /get \n Para eliminar "
            "tu subscripción, envía el comando /unsubscribe.")

    UNSUBSCRIBED = (
            "Ya no estás subscrito, para volver a estarlo, envía /subscribe.")

    SET_RUT = ("Rut:%s guardado correctamente\n Envía /get para consultar "
               "directamente. Y recuerda que enviando /subscribe revisaré "
               "periodicaménte la página del banco para avisarte tan pronto "
               "detecte cambios.")

    # ####################################### #
    # ######## User errors messages. ######## #
    # ####################################### #

    NO_RUT_MSG = (
            "Tu rut no está almacenado, envía '/set <RUT>' para almacenarlo.")

    SET_EMPTY_RUT = "Especifica el rut para poder guardarlo."

    SET_INVALID_RUT = ("Rut no válido, recuerda agregar el dígito verificador "
                       "separado por un guión.")
    UNSUBSCRIBE_NON_SUBSCRIBED = "No estás subscrito."

    SUBSCRIBE_NO_RUT = (
            "Tienes que tener un rut registrado para poder subscribirte, "
            "utiliza /set <RUT> para registrar un rut.")

    ALREADY_SUBSCRIBED = "Ya estás registrado."

    LOOKS_LIKE_RUT = (
            "Esto parece ser un rut, para ingresar un rut por favor incluye "
            "el digito verificador separado por un guión (-)")

    FROM_NON_PRIVATE_CHAT = (
            "Lamentablemente de momento solo soportamos chats privados con el "
            "bot."
    )

    # ####################################### #
    # ###### Web parser err messages. ####### #
    # ####################################### #

    CLIENTE_ERROR = ("Eres cliente del banco?, no es posible consultar tu "
                     "informacion por la interfaz publica.")

    INTENTE_NUEVAMENTE_ERROR = (
            "La página del banco retornó con error y dice que intentes "
            "nuevamente. Intenta nuevamente en unas horas.")

    NO_PAGOS = "Actualmente no hay pagos a tu favor."

    # ####################################### #
    # ###### Internal error messages. ####### #
    # ####################################### #

    INTERNAL_ERROR = ("¡Ups! Un error inesperado ha ocurrido, lo "
                      "solucionaremos a la brevedad (?)")

    PARSER_ERROR = ("No pude parser la respuesta del banco :(. "
                    "Espero que pronto algún humano solucione esto.")
