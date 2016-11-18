import itertools
import re

#Robado desde https://gist.github.com/rbonvall/464824
def digito_verificador(rut):
    reversed_digits = map(int, reversed(str(rut)))
    factors = itertools.cycle(range(2, 8))
    s = sum(d * f for d, f in zip(reversed_digits, factors))
    return 'k' if (-s) % 11 == 10 else (-s) % 11


def normalize_rut(rut_input):
    no_digito = remove_digito_verificador_puntos(rut_input)
    if not no_digito:
        return None
    return no_digito


def remove_digito_verificador_puntos(rut_input):
    reg = re.compile("^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}-?[Kk0-9]?")
    if not reg.match(rut_input):
        return ""
    return re.sub("-[kK0-9]", "", re.sub("\.", "",  rut_input)).lstrip("0")

def get_vales_vista(rut):
    get_webpage(rut, digito_verificador(rut))
