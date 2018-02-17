import codecs
from collections import OrderedDict
import datetime
from enum import Enum
import logging
import requests
from typing import Dict, List

from src.model_interface import CachedResult, User
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
    DEPRECATED_NOT_PARSED = 4


class Event(object):
    def __init__(self, event_type: TypeOfEvent, date: datetime.date) -> None:
        self.event_type = event_type
        self.date = date


class DeprecatedEvent(Event):
    def __init__(self, string_representation) -> None:
        self.string_representation = string_representation
        self.event_type = TypeOfEvent.DEPRECATED_NOT_PARSED


class TypeOfWebResult(Enum):
    NO_ERROR = 1
    CLIENTE = 2
    INTENTE_NUEVAMENTE = 3


class WebResult(object):
    _CLIENTE_ERROR = ("Eres cliente del banco?, no es posible consultar tu "
                      "informacion por la interfaz publica.")
    _INTENTE_NUEVAMENTE_ERROR = (
            "La pagina del banco tiene un error y dice que intentes "
            "nuevamente. Intenta nuevamente en unas horas")

    def __init__(
            self, type_result: TypeOfWebResult, events: List[Event]) -> None:
        self._type_result = type_result
        self._events = events

    def get_type(self):
        return self._type_result

    def get_events(self):
        return self._events

    def get_error(self):
        type_result = self._type_result
        if type_result == TypeOfWebResult.CLIENTE:
            return self._CLIENTE_ERROR
        elif type_result == TypeOfWebResult.INTENTE_NUEVAMENTE:
            return self._INTENTE_NUEVAMENTE_ERROR
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
            day = int(split[0])
            month = int(split[1])
            year = int(split[2])
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
    def _raw_events_to_new_events(cls,
                                  raw_events: List[Dict[str, str]]):
        ret = []
        for event in raw_events:
            date = cls._parse_date(event['Fecha de Pago'])
            event_type = cls._parse_event_type(event['Estado'])
            ret.append(Event(event_type, date))
        return ret

    @classmethod
    def raw_events_to_new_events(cls, events: List[Dict[str, str]]):
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
        return events

    @classmethod
    def _raw_event_to_single_cache_string(cls,
                                          raw_event: Dict[str, str]) -> str:
        ret = []
        for k, v in raw_event.items():
            ret.append("%s: %s\n" % (k.strip(), v.strip()))
        return "".join(ret).rstrip("\n")

    @classmethod
    def _raw_events_to_cache_string(cls, raw_events: List[Dict[str, str]]):
        parsed_result = []
        for e in raw_events:
            this_result = []
            for k, v in e.items():
                this_result.append("%s: %s\n" % (k.strip(), v.strip()))
            parsed_result.append("".join(this_result).rstrip("\n"))
        return "\n\n".join(parsed_result)

    @classmethod
    def _single_cache_string_to_raw_event(cls, string):
        d = OrderedDict()
        lines = string.split("\n")
        if len(lines) != 4:
            raise ParsingException('4 lines expected, got %d.', len(lines))
        d['Fecha de Pago'] = lines[0].lstrip('Fecha de Pago ')
        d['Medio de Pago'] = lines[1].lstrip('Medio de Pago ')
        d['Oficina/Banco'] = lines[2].lstrip('Oficina/Banco ')
        d['Estado'] = lines[3].lstrip('Estado ')
        return d

    @classmethod
    def cache_string_to_raw_events(cls, cache_string: str):
        single_cache_strings = cache_string.split("\n\n")
        raw_events = []
        for s in single_cache_strings:
            raw_events.append(cls._single_cache_string_to_raw_event(s))
        return raw_events

    @classmethod
    def deprecated_events_list_to_cache_string(cls, deprecated_events):
        strings = []
        for e in deprecated_events:
            strings.append(e.string_representation)
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

        ret: List[Event] = []
        for r in raw_events:
            ret.append(
                    DeprecatedEvent(cls._raw_event_to_single_cache_string(r)))
        return WebResult(TypeOfWebResult.NO_ERROR, ret)


class Web(object):

    def __init__(self, rut: Rut, telegram_user_id: int,
                 web_retriever: WebRetriever=WebPageDownloader()) -> None:
        self.rut = rut
        self._retrieve(telegram_user_id, web_retriever)
        try:
            self._parse_new_results()
        except Exception:
            self._events = None
            pass

    def _retrieve(self, telegram_user_id: int, web_retriever: WebRetriever):
        user_id = User.get_id(telegram_user_id)
        cached_results = CachedResult.get(user_id, self.rut)
        self._loaded_from_cache = cached_results is not None
        if cached_results:
            self._old_parsed_results = cached_results
            return
        raw_page = web_retriever.retrieve(self.rut)
        deprecated_web_result = Parser.parse(raw_page)
        self._old_parsed_results = (
                Parser.deprecated_events_list_to_cache_string(
                        deprecated_web_result.get_events()))
        self._cache_changed = True
        try:
            self._cache_changed = CachedResult.update(
                    user_id, self.rut, self._old_parsed_results)
        # Non fatal error.
        except Exception as e:
            logging.exception("Unable to update the cache")

    # Must be called after retrieve returns.
    def _parse_new_results(self):
        raw_events = Parser.cache_string_to_raw_events(
                self._old_parsed_results)
        self._events = raw_events_to_new_events(raw_events)

    def get_results(self):
        return self._old_parsed_results

    def did_cache_change(self):
        return self._cache_changed
