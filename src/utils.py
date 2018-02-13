from contextlib import contextmanager
import datetime
import itertools
import sys
from typing import Optional, Type, Union
import re
import pytz


class Rut(object):
    def __init__(self, rut: int, digito_verificador: str):
        self.rut_sin_digito = rut
        self.digito_verificador = digito_verificador

    def __str__(self):
        return '%d-%s' % (self._sin_digito_verificador,
                          self._digito_verificador)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def build_rut(cls, rut: str):
        """Crea un rut a partir de un string.

        Hace todo lo posible por construir un rut, acepta strings con y sin
        puntos separadores y digito verificador. Si no detecta el input como
        rut retorna None.
        """
        rut_sin_digito = cls._normalize_rut(rut)
        if rut_sin_digito is None:
            return None
        num_rut = int(rut_sin_digito)
        return Rut(num_rut, cls._digito_verificador(rut_sin_digito))

    # Robado desde https://gist.github.com/rbonvall/464824
    @classmethod
    def _digito_verificador(cls, rut: str) -> str:
        reversed_digits = map(int, reversed(rut))
        factors = itertools.cycle(range(2, 8))
        s = sum(d * f for d, f in zip(reversed_digits, factors))
        return 'k' if (-s) % 11 == 10 else (-s) % 11

    @classmethod
    def _normalize_rut(cls, rut_input: str) -> Optional[str]:
        rut_sin_digito = cls._remove_digito_verificador_puntos(rut_input)
        if not rut_sin_digito:
            return None
        expected_digito_ver = cls._digito_verificador(rut_sin_digito)
        # Si el digito verificador estaba malo.
        if (rut_input[-1].lower() != expected_digito_ver and
                rut_input[-1] != rut_sin_digito[-1]):
            return None

        return rut_sin_digito

    @classmethod
    def _remove_digito_verificador_puntos(cls, rut: str) -> Optional[str]:
        # This regex defines a RUT.
        reg = re.compile('^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}(-[Kk0-9])$')
        match = reg.match(rut)
        # Check if run_input is a rut.
        if not match:
            return None
        dot_and_leading_zero_removed = re.sub('\.', '',  rut).lstrip('0')
        if not match.group(1):
            return dot_and_leading_zero_removed
        else:  # Remover el digito verificador con guion, si es que tiene
            return dot_and_leading_zero_removed[:-len(match.group(1))]


# Check whether is a proper time to send an automated message to an user.
def is_a_proper_time(now: datetime.datetime) -> bool:
    """

    :param now: utc time to check if is proper
    :return:
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        now = now.replace(tzinfo=pytz.utc)

    cl_tz = pytz.timezone('America/Santiago')
    normalized_now = now.astimezone(cl_tz)

    # If saturday or sunday
    if normalized_now.weekday() > 4:
        return bool(False)  # To make pytype happy.

    # If between 00:00 and 9:59.
    if normalized_now.hour < 10:
        return bool(False)

    return bool(True)
