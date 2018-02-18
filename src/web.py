import codecs
from collections import OrderedDict
import datetime
from enum import Enum
import logging
import requests
from typing import Dict, List

from src.messages import Messages
from src.model_interface import Cache, User
from src.utils import Rut

import bs4

logger = logging.getLogger(__name__)


class ParsingException(Exception):
    def __init__(self, public_message):
        super(ParsingException, self).__init__(public_message)
        self.public_message = public_message


class TypeOfEvent(Enum):
    VIGENTE_EN_RENDICION = 1  # El vale vista va a estar en la fecha que dice.
    VIGENTE_RENDIDO = 2  # Listo para retirar.
    PAGADO_RENDIDO = 3  # Ya fue cobrado/retirado.
    RAW_NOT_PARSED = 4


class Event(object):
    def __init__(self, event_type: TypeOfEvent, date: datetime.date) -> None:
        self.event_type = event_type
        self.date = date


class RawEvent(Event):
    def __init__(self, ordered_dict: Dict[str, str]) -> None:
        self._ordered_dict = ordered_dict
        self._str_repr = None
        self.event_type = TypeOfEvent.RAW_NOT_PARSED

    def string_representation(self):
        if self._str_repr is None:
            acc = []
            for k, v in self._ordered_dict.items():
                acc.append("%s: %s\n" % (k.strip(), v.strip()))
            self._str_repr = "".join(acc).rstrip("\n")
        return self._str_repr

    def get_date(self) -> str:
        return self._ordered_dict['Fecha de Pago']

    def get_status(self) -> str:
        return self._ordered_dict['Estado']

    def __str__(self):
        return self.string_representation()


class TypeOfWebResult(Enum):
    NO_ERROR = 1
    CLIENTE = 2
    INTENTE_NUEVAMENTE = 3


class WebResult(object):

    def __init__(
            self, type_result: TypeOfWebResult, events: List[Event]) -> None:
        self._type_result = type_result
        self._events = events  # type: List[Event]

    def get_type(self):
        return self._type_result

    def get_events(self):
        return self._events

    def get_error(self):
        type_result = self._type_result
        if type_result == TypeOfWebResult.CLIENTE:
            return Messages.CLIENTE_ERROR
        elif type_result == TypeOfWebResult.INTENTE_NUEVAMENTE:
            return Messages.INTENTE_NUEVAMENTE_ERROR
        elif type_result == TypeOfWebResult.NO_ERROR:
            return ''
        raise ValueError('Unknown type of result')


class WebRetriever(object):
    def retrieve(self, rut: Rut):
        raise NotImplementedError()


class WebPageDownloader(WebRetriever):
    URL = ("http://www.empresas.bancochile.cl/cgi-bin/cgi_cpf?"
           "rut1=60910000&dv1=1&canal=BCW&tipo=2&BEN_DIAS=90"
           "&mediopago=99&rut2=%s&dv2=%s")

    def retrieve(self, rut: Rut):
        url = self.URL % (rut.rut_sin_digito, rut.digito_verificador)
        try:
            r = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.exception("Connection error")
            raise ParsingException(("Error de conexion, (probablemente) "
                                    "estamos trabajando para solucionarlo."))
        if(r.status_code != 200):
            logger.warn("Couldn't get the page, error %s:%s" % (r.status_code,
                                                                r.reason))
            raise ParsingException(("Error de conexion, (probablemente) "
                                    "estamos trabajando para solucionarlo."))

        return r.text


class Parser(object):
    @classmethod
    def _parse_date(cls, date: str) -> datetime.date:
        split = date.split('/')
        try:
            day = int(split[0].strip())
            month = int(split[1].strip())
            year = int(split[2].strip())
            return datetime.date(year, month, day)
        except Exception:
            logger.error('Could not parse a date: %s', date)
            raise ParsingException('No pude parsear la pagina del banco.')

    @classmethod
    def _parse_event_type(cls, event_type: str) -> TypeOfEvent:
        event = event_type.lower()
        if 'pagado' in event and 'rendido' in event:
            return TypeOfEvent.PAGADO_RENDIDO
        if 'vigente' in event and 'rendido' in event:
            return TypeOfEvent.VIGENTE_RENDIDO
        if ('vigente' in event and
                ('rendición' in event or 'rendicion' in event)):
            return TypeOfEvent.VIGENTE_EN_RENDICION
        logger.error('Unable to parse event_type:%s', event_type)
        raise ParsingException('No pude parsear la respuesta del banco :(')

    @classmethod
    def _raw_events_to_new_events(cls, raw_events: List[RawEvent]):
        ret = []
        for event in raw_events:
            date = cls._parse_date(event.get_date())
            event_type = cls._parse_event_type(event.get_status())
            ret.append(Event(event_type, date))
        return ret

    @classmethod
    def raw_events_to_new_events(cls, events: List[RawEvent]) -> List[Event]:
        # Experimental, errors here are not fatal.
        try:
            return cls._raw_events_to_new_events(events)
        except Exception as e:
            logger.exception('While trying to parse:\n%s\n', events)
            return []

    @classmethod
    def _raw_page_to_raw_events(cls, raw_page):
        soup = bs4.BeautifulSoup(raw_page, "html.parser")
        table = soup.body.form.find_all(
                'table')[1].find_all('tr')[5].find_all('tr')
        if table[0].td.text != '\nFecha de Pago':
            logger.error('Unexpected webpage:\n%s', raw_page)
            raise ParsingException('No pude parsear la respuesta del banco.')
        events = []
        for i in range(1, len(table) - 1):
            data = table[i].find_all('td')
            events.append(
                    OrderedDict([('Fecha de Pago', data[0].text.strip('\n')),
                                 ('Medio de Pago', data[1].text.strip('\n')),
                                 ('Oficina/Banco', data[2].text.strip('\n')),
                                 ('Estado', data[3].text.strip('\n'))]))
        return [RawEvent(d) for d in events]

    @classmethod
    def _raw_events_to_cache_string(cls, raw_events: List[RawEvent]):
        raw_events_as_str = [str(x) for x in raw_events]
        return "\n\n".join(raw_events_as_str)

    @classmethod
    def _single_cache_string_to_raw_event(cls, string: str) -> RawEvent:
        d = OrderedDict()  # type: Dict[str, str]
        lines = string.split("\n")
        if len(lines) != 4:
            raise ParsingException('4 lines expected, got %d.' % len(lines))
        d['Fecha de Pago'] = lines[0].lstrip('Fecha de Pago: ')
        d['Medio de Pago'] = lines[1].lstrip('Medio de Pago: ')
        d['Oficina/Banco'] = lines[2].lstrip('Oficina/Banco: ')
        d['Estado'] = lines[3].lstrip('Estado: ')
        return RawEvent(d)

    @classmethod
    def cache_string_to_web_result(cls, cache_string: str) -> WebResult:
        if Messages.CLIENTE_ERROR in cache_string:
            return WebResult(TypeOfWebResult.CLIENTE, [])
        if Messages.INTENTE_NUEVAMENTE_ERROR in cache_string:
            return WebResult(TypeOfWebResult.INTENTE_NUEVAMENTE, [])

        single_cache_strings = cache_string.split("\n\n")
        raw_events = []  # type: List[Event]
        for s in single_cache_strings:
            raw_events.append(cls._single_cache_string_to_raw_event(s))
        return WebResult(TypeOfWebResult.NO_ERROR, raw_events)

    @classmethod
    def raw_events_to_cache_string(cls, raw_events: List[RawEvent]):
        strings = [str(e) for e in raw_events]
        return "\n\n".join(strings)

    @classmethod
    def parse(cls, raw_page) -> WebResult:
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
            raw_events = cls._raw_page_to_raw_events(raw_page)
        except Exception as e:
            logger.exception('While trying to parse \n%s\n', raw_page)
            raise e

        return WebResult(TypeOfWebResult.NO_ERROR, raw_events)


class Web(object):

    def __init__(self, rut: Rut, telegram_user_id: int,
                 web_retriever: WebRetriever=WebPageDownloader(),
                 cache: Cache=Cache()) -> None:
        self.rut = rut
        self._retrieve(telegram_user_id, web_retriever, cache)
        try:
            self._parse_new_results()
        except Exception as e:
            self._events = None
            logger.exception('New results parsing failed.')

    def _retrieve(self, telegram_user_id: int, web_retriever: WebRetriever,
                  cache: Cache):
        user_id = User.get_id(telegram_user_id)
        cached_results = cache.get(user_id, self.rut)
        self._retrieved_from_cache = cached_results is not None
        self._cache_changed = False
        if cached_results:
            self._old_cache_and_user_str = cached_results
            self.raw_events_web_result = Parser.cache_string_to_web_result(
                    cached_results)
            return

        raw_page = web_retriever.retrieve(self.rut)
        raw_events_web_result = Parser.parse(raw_page)

        # Cache even error results to prevent users to trigger
        # too many requests to the bank.
        if raw_events_web_result.get_type() != TypeOfWebResult.NO_ERROR:
            self._old_cache_and_user_str = raw_events_web_result.get_error()
        else:
            self._old_cache_and_user_str = Parser.raw_events_to_cache_string(
                    raw_events_web_result.get_events())
        try:
            self._cache_changed = cache.update(user_id, self.rut,
                                               self._old_cache_and_user_str)
        # Non fatal error.
        except Exception as e:
            logger.exception("Unable to update the cache")
        self.raw_events_web_result = raw_events_web_result

    # Must be called after retrieve returns.
    def _parse_new_results(self):
        raw_events = self.raw_events_web_result.get_events()
        self._events = Parser.raw_events_to_new_events(raw_events)

    def get_results(self):
        return self._old_cache_and_user_str

    def did_cache_change(self):
        return self._cache_changed

    def is_useful_info_for_user(self) -> bool:
        web_result_type = self.raw_events_web_result.get_type()
        # If error, not useful.
        if web_result_type != TypeOfWebResult.NO_ERROR:
            return False
        # If empty, not useful.
        if not self._old_cache_and_user_str:
            return False
        # If the info was already in the cache, not useful.
        if not self.did_cache_change():
            return False
        # TODO(fmontoto): Check if there is useful new data in the result.
        return True
