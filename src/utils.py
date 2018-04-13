"""Some utility classes and methods."""
import datetime
import itertools
from typing import Optional
import re
import pytz


class Rut(object):
    """Represents a chilean RUT."""
    def __init__(self, rut: int, digito_verificador: str) -> None:
        self.rut_sin_digito = rut
        self.digito_verificador = digito_verificador

    def __str__(self):
        # Do this with locale
        tmp = "{:,}-{}".format(self.rut_sin_digito, self.digito_verificador)
        return tmp.replace(',', '.')

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        # pylint: disable=unidiomatic-typecheck
        return (type(self) == type(other) and
                self.rut_sin_digito == other.rut_sin_digito and
                self.digito_verificador == other.digito_verificador)

    @classmethod
    def build_rut(cls, rut: str) -> Optional['Rut']:
        """Crea un rut a partir de un string.

        Hace todo lo posible por construir un rut, guin i digito verificador
        son requeridos. Si no detecta el input como rut retorna None.
        """
        rut_sin_digito = cls._normalize_rut(rut)
        if rut_sin_digito is None:
            return None
        num_rut = int(rut_sin_digito)
        return Rut(num_rut, cls._digito_verificador(rut_sin_digito))

    @classmethod
    def build_rut_sin_digito(cls, rut: str) -> 'Rut':
        """Crea un rut a partir de un string sin digito verificador."""
        rut_no_dots = rut.replace(',', '')
        digito = cls._digito_verificador(rut_no_dots)
        return Rut(int(rut_no_dots), digito)

    # Robado desde https://gist.github.com/rbonvall/464824
    @classmethod
    def _digito_verificador(cls, rut: str) -> str:
        reversed_digits = map(int, reversed(rut))
        factors = itertools.cycle(range(2, 8))
        acc = sum(d * f for d, f in zip(reversed_digits, factors))
        return 'k' if (-acc) % 11 == 10 else str((-acc) % 11)

    @classmethod
    def _normalize_rut(cls, rut_input: str) -> Optional[str]:
        rut_sin_digito = cls._remove_digito_verificador_puntos(rut_input)
        if not rut_sin_digito:
            return None
        expected_digito_ver = cls._digito_verificador(rut_sin_digito)
        # Si el digito verificador estaba malo.
        if rut_input[-1].lower() != str(expected_digito_ver):
            return None

        return rut_sin_digito

    @classmethod
    def _remove_digito_verificador_puntos(cls, rut: str) -> Optional[str]:
        # This regex defines a RUT.
        reg = re.compile(r'^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}(-[Kk0-9])$')
        match = reg.match(rut)
        # Check if run_input is a rut.
        if not match:
            return None
        dot_and_leading_zero_removed = re.sub(r'\.', '', rut).lstrip('0')
        if not match.group(1):
            return dot_and_leading_zero_removed
        # Si tiene, remover el digito verificador con guion.
        return dot_and_leading_zero_removed[:-len(match.group(1))]

    @staticmethod
    def looks_like_rut(rut: str):
        """True if the string looks like a rut."""
        clean_rut = rut.replace('.', '').strip()
        reg = re.compile('^[0-9]{7,9}[0-9k]?$')
        match = reg.match(clean_rut)
        if match:
            return True
        return False


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
