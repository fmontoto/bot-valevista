"""Module to retrieve and parse results from the bank web page."""

from collections import OrderedDict
import datetime
from enum import Enum
import logging
from typing import Dict, List
import urllib.error
import urllib.request as pyrequest

import bs4

from src.messages import Messages
from src.model_interface import Cache, DbConnection, User
from src.utils import Rut


logger = logging.getLogger('bot_main_logger')  # pylint: disable=invalid-name


class ParsingException(Exception):
    """Error when trying to parse results."""
    def __init__(self, public_message):
        super(ParsingException, self).__init__(public_message)
        self.public_message = public_message


class Event(object):
    """Object that represents each event for a specific rut."""
    def __init__(self, fecha: str, medio_pago: str, oficina: str,
                 estado: str) -> None:
        self._str_repr = None
        self._ordered_dict: Dict[str, str] = OrderedDict([
                ('Fecha de Pago', fecha),
                ('Medio de Pago', medio_pago),
                ('Oficina/Banco', oficina),
                ('Estado', estado)])

    def _string_representation(self):
        if self._str_repr is None:
            acc = []
            for key, val in self._ordered_dict.items():
                acc.append("%s: %s\n" % (key.strip(), val.strip()))
            self._str_repr = "".join(acc).rstrip("\n")
        return self._str_repr

    @classmethod
    def is_useful(cls):
        """Whether this event is useful for the user or not."""
        raise NotImplementedError()

    def __str__(self):
        return self._string_representation()

    @staticmethod
    def build_event(fecha: str, medio_pago: str, oficina: str, estado: str):
        """Builds an event from the given parameters."""
        estado_lower = estado.lower()
        if 'pagado' in estado_lower and 'rendido' in estado_lower:
            return EventPagadoRendido(fecha, medio_pago, oficina, estado)
        if 'vigente' in estado_lower and 'rendido' in estado_lower:
            return EventVigenteRendido(fecha, medio_pago, oficina, estado)
        if ('vigente' in estado_lower and ('rendición' in estado_lower or
                                           'rendicion' in estado_lower)):
            return EventVigenteEnRendicion(fecha, medio_pago, oficina, estado)
        logger.error('Unable to parse event:%s', estado)
        return EventUnknown(fecha, medio_pago, oficina, estado)

    @staticmethod
    def build_event_from_cache_entry(entry: str):
        """Builds an event from a single cache entry."""
        lines = entry.split("\n")
        if len(lines) != 4:
            logger.error('4 lines expected, got %d:%s', len(lines), entry)
            raise ParsingException(Messages.PARSER_ERROR)
        fecha = lines[0].lstrip('Fecha de Pago: ')
        medio_pago = lines[1].lstrip('Medio de Pago: ')
        oficina = lines[2].lstrip('Oficina/Banco: ')
        estado = lines[3].lstrip('Estado: ')
        return Event.build_event(fecha, medio_pago, oficina, estado)


class EventVigenteRendido(Event):
    """ Listo para retirar."""

    @classmethod
    def is_useful(cls):
        return True


class EventVigenteEnRendicion(Event):
    """Va a estar disponible para cobrar en la fecha especificada."""

    @classmethod
    def is_useful(cls):
        return True


class EventPagadoRendido(Event):
    """Ya fue cobrado."""

    @classmethod
    def is_useful(cls):
        return False


class EventUnknown(Event):
    """Evento desconocido."""

    @classmethod
    def is_useful(cls):
        return True  # If we don't know about it, may be useful.


class TypeOfWebResult(Enum):
    """Types of results."""
    NO_ERROR = 1
    CLIENTE = 2
    INTENTE_NUEVAMENTE = 3


class WebResult(object):
    """Parsed response from the web page."""
    def __init__(
            self, type_result: TypeOfWebResult, events: List[Event]) -> None:
        self._type_result = type_result
        self._events = events  # type: List[Event]

    def get_type(self):
        """Returns the type of the result."""
        return self._type_result

    def get_events(self):
        """Returns result's events."""
        return self._events

    def get_error(self):
        """On error, returns a proper string to show to the user."""
        type_result = self._type_result
        if type_result == TypeOfWebResult.CLIENTE:
            return Messages.CLIENTE_ERROR
        elif type_result == TypeOfWebResult.INTENTE_NUEVAMENTE:
            return Messages.INTENTE_NUEVAMENTE_ERROR
        elif type_result == TypeOfWebResult.NO_ERROR:
            return ''
        raise ValueError('Unknown type of result')


class WebRetriever(object):  # pylint: disable=too-few-public-methods
    """Base class for webpage retrievers."""
    def retrieve(self, rut: Rut):
        """Each instance should implement this function.

        Should return the retrieved web page.
        """
        raise NotImplementedError()


# pylint: disable=too-few-public-methods
class WebPageDownloader(WebRetriever):
    """Class to download a webpage."""

    HEADERS = {
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/68.0.3440.106 Safari/537.36'),
            'Accept': ('text/html,application/xhtml+xml,application/xml;q=0.9,'
                       'image/webp,image/apng,*/*;q=0.8'),
            # urllib is not properly handling gzip-ed responses.
            # Ask the server not to send gzip-ed data.
            # 'Accept-Encoding': 'gzip, deflate',
            'Accept-Encoding': 'identity',
            'Accept-Language': 'en-US,en;q=0.9,es-CL;q=0.8,es;q=0.7',
    }

    PARAMS = (
            ('canal', 'BCW'),
            ('tipo', '2'),
            ('BEN_DIAS', '90'),
            ('rut1', '60910000'),
            ('dv1', '1'),
            ('mediopago', '99'),
    )

    URL = 'http://www.empresas.bancochile.cl/cgi-bin/cgi_cpf'

    def retrieve(self, rut: Rut) -> str:
        """Downloads the web page corresponding to 'rut'."""

        params = self.PARAMS + (('rut2', str(rut.rut_sin_digito)),
                                ('dv2', rut.digito_verificador))
        parameters = ["%s=%s" % (t[0], t[1]) for t in params]
        url = self.URL + "?" + "&".join(parameters)
        try:
            req = pyrequest.urlopen(pyrequest.Request(url,
                                                      headers=self.HEADERS))
        except urllib.error.URLError:
            logger.exception("Connection error")
            raise ParsingException(("Error de conexion, (probablemente) "
                                    "estamos trabajando para solucionarlo."))
        except Exception:
            logger.exception("Unexpected error at retrieve")
            raise ParsingException(("Error de conexion, (probablemente) "
                                    "estamos trabajando para solucionarlo."))

        response_bytes = req.read()
        charset = (req.headers.get_content_charset()  # type: ignore
                or req.info().get_content_charset()  # type: ignore
                   or 'utf-8')
        return response_bytes.decode(charset)


class Parser(object):
    """Class to parse the bank web page."""
    @classmethod
    def _parse_date(cls, date: str) -> datetime.date:
        """Parse a dd/mm/yyyy date into a date object."""
        split = date.split('/')
        try:
            day = int(split[0].strip())
            month = int(split[1].strip())
            year = int(split[2].strip())
            return datetime.date(year, month, day)
        except Exception:
            logger.exception('Could not parse a date: %s', date)
            raise ParsingException(Messages.PARSER_ERROR)

    @classmethod
    def _raw_page_to_events(cls, raw_page):
        soup = bs4.BeautifulSoup(raw_page, "html.parser")
        table = soup.body.form.find_all(
                'table')[1].find_all('tr')[5].find_all('tr')
        if table[0].td.text != '\nFecha de Pago':
            logger.error('Unexpected webpage:\n%s', raw_page)
            raise ParsingException(Messages.PARSER_ERROR)
        events = []
        for i in range(1, len(table) - 1):
            data = table[i].find_all('td')
            fecha = data[0].text.strip('\n')
            medio_pago = data[1].text.strip('\n')
            oficina = data[2].text.strip('\n')
            estado = data[3].text.strip('\n')
            events.append(
                    Event.build_event(fecha, medio_pago, oficina, estado))
        return events

    @classmethod
    def _events_to_cache_string(cls, events: List[Event]):
        events_as_str = [str(x) for x in events]
        return "\n\n".join(events_as_str)

    @classmethod
    def cache_string_to_web_result(cls, cache_string: str) -> WebResult:
        """Builds a web results form the string stored in the cache."""
        if Messages.CLIENTE_ERROR in cache_string:
            return WebResult(TypeOfWebResult.CLIENTE, [])
        if Messages.INTENTE_NUEVAMENTE_ERROR in cache_string:
            return WebResult(TypeOfWebResult.INTENTE_NUEVAMENTE, [])
        if Messages.NO_PAGOS in cache_string:
            return WebResult(TypeOfWebResult.NO_ERROR, [])

        single_cache_entries = cache_string.split("\n\n")
        events = []  # type: List[Event]
        for cache_entry in single_cache_entries:
            events.append(Event.build_event_from_cache_entry(cache_entry))
        return WebResult(TypeOfWebResult.NO_ERROR, events)

    @classmethod
    def events_to_cache_string(cls, events: List[Event]):
        """Convert a list of events into a cache string."""
        if not events:
            return Messages.NO_PAGOS
        strings = [str(e) for e in events]
        return "\n\n".join(strings)

    @classmethod
    def parse(cls, raw_page) -> WebResult:
        """Parses raw_page to a WebResult with the events in the page."""
        if "Para clientes del Banco de Chile" in raw_page:
            logger.debug('Parsed cliente.')
            return WebResult(TypeOfWebResult.CLIENTE, [])
        if "Por ahora no podemos atenderle." in raw_page:
            logger.debug('Parsed pagina no disponible.')
            return WebResult(TypeOfWebResult.INTENTE_NUEVAMENTE, [])
        if "Actualmente no registra pagos a su favor" in raw_page:
            logger.debug('Parsed pagina vacia.')
            return WebResult(TypeOfWebResult.NO_ERROR, [])

        try:
            events = cls._raw_page_to_events(raw_page)
        except Exception as exception:
            logger.exception('While trying to parse \n%s\n', raw_page)
            raise exception

        return WebResult(TypeOfWebResult.NO_ERROR, events)


class Web(object):
    """Class that queries and represents a web response from the bank."""
    def __init__(self, db_connection: DbConnection, rut: Rut,
                 telegram_user_id: int, cache: Cache,
                 web_retriever: WebRetriever = WebPageDownloader()) -> None:
        self.rut = rut
        self._db_connection = db_connection
        self._retrieve(telegram_user_id, web_retriever, cache)

    def _retrieve(self, telegram_user_id: int, web_retriever: WebRetriever,
                  cache: Cache):
        user_id = User(self._db_connection).get_id(telegram_user_id)
        cached_results = cache.get(user_id, self.rut)
        self._retrieved_from_cache = cached_results is not None
        self._cache_changed = False
        if cached_results:
            self._old_cache_and_user_str = cached_results
            self.web_result = Parser.cache_string_to_web_result(
                    cached_results)
            return

        raw_page = web_retriever.retrieve(self.rut)
        web_result = Parser.parse(raw_page)

        # Cache even error results to prevent users to trigger
        # too many requests to the bank.
        if web_result.get_type() != TypeOfWebResult.NO_ERROR:
            self._old_cache_and_user_str = web_result.get_error()
        else:
            self._old_cache_and_user_str = Parser.events_to_cache_string(
                    web_result.get_events())
        try:
            self._cache_changed = cache.update(user_id, self.rut,
                                               self._old_cache_and_user_str)
        # Non fatal error.
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unable to update the cache")
        self.web_result = web_result

    def get_results(self):
        """Get results' string to be send to the user."""
        return self._old_cache_and_user_str

    def _did_cache_change(self):
        return self._cache_changed

    def _any_useful_event(self):
        for event in self.web_result.get_events():
            if event.is_useful():
                return True
        return False

    def is_useful_info_for_user(self) -> bool:
        """Whether the data in this result is useful for the user or not."""
        web_result_type = self.web_result.get_type()
        # If error, not useful.
        if web_result_type != TypeOfWebResult.NO_ERROR:
            return False
        # If empty, not useful.
        if not self._old_cache_and_user_str:
            return False
        # If the info was already in the cache, not useful.
        if not self._did_cache_change():
            return False
        # If no results, not useful.
        if not self.web_result.get_events():
            return False
        # If there is no useful event, not useful.
        if not self._any_useful_event():
            return False
        return True
