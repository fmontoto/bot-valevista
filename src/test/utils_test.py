import unittest
from unittest import TestCase

from src.utils import Rut


class TestRutClassMethods(TestCase):

    def test_digito_verificador(self):
        self.assertEqual(2, Rut._digito_verificador("12456371"))
        self.assertEqual(4, Rut._digito_verificador("6786532"))
        self.assertEqual(8, Rut._digito_verificador("6786530"))
        self.assertEqual(1, Rut._digito_verificador("6786539"))
        self.assertEqual('k', Rut._digito_verificador("14123742"))

    def test_normalize_rut(self):
        self.assertEqual('18123021', Rut._normalize_rut('18.123.021-1'))
        self.assertEqual(None, Rut._normalize_rut('18.123.021-2'))
        self.assertEqual('18123021', Rut._normalize_rut('18.123021-1'))
        self.assertEqual('18123021', Rut._normalize_rut('18123.021-1'))
        self.assertEqual('18123021', Rut._normalize_rut('18123.0211'))

        self.assertEqual(None, Rut._normalize_rut('18.123.0212'))
        self.assertEqual(None, Rut._normalize_rut('181230212'))
        self.assertEqual('2343234',
                         Rut._remove_digito_verificador_puntos("2343234k"))


    def test_remove_digito_verificador_puntos(self):
        self.assertEqual("12444333",
                         Rut._remove_digito_verificador_puntos("12.444.333-3"))
        self.assertEqual("3324324",
                         Rut._remove_digito_verificador_puntos("3.324.324-2"))
        self.assertEqual("3324324",
                         Rut._remove_digito_verificador_puntos("03.324.324-2"))
        self.assertEqual("3432345",
                         Rut._remove_digito_verificador_puntos("3.432.345-1"))
        self.assertEqual("3432345",
                         Rut._remove_digito_verificador_puntos("3.4323455"))
        self.assertEqual("3432345",
                         Rut._remove_digito_verificador_puntos("3.432345-5"))
        self.assertEqual("2343234",
                         Rut._remove_digito_verificador_puntos("2343234-k"))
        self.assertEqual("2343234",
                         Rut._remove_digito_verificador_puntos("2343234-K"))
        self.assertEqual("2343234",
                         Rut._remove_digito_verificador_puntos("2343234k"))


class TestRutObject(TestCase):
    def test_simple(self):
        rut = Rut.build_rut('2343234K')
        self.assertEqual(2343234, rut._sin_digito_verificador)
        self.assertEqual('k', rut._digito_verificador)

if __name__ == '__main__':
    unittest.main()
