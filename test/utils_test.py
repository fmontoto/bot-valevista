from unittest import TestCase

from src.utils import remove_digito_verificador_puntos, digito_verificador


class TestRut(TestCase):
    def test_remove_digito_verificador_puntos(self):
        self.assertEqual("12444333",
                         remove_digito_verificador_puntos("12.444.333-3"))
        self.assertEqual("3324324",
                         remove_digito_verificador_puntos("3.324.324-2"))
        self.assertEqual("3324324",
                         remove_digito_verificador_puntos("03.324.324-2"))
        self.assertEqual("3432345",
                         remove_digito_verificador_puntos("3.432.345"))
        self.assertEqual("3432345",
                         remove_digito_verificador_puntos("3.432345"))
        self.assertEqual("3432345",
                         remove_digito_verificador_puntos("3.432345-2"))
        self.assertEqual("2343234",
                         remove_digito_verificador_puntos("2343234-k"))
        self.assertEqual("2343234",
                         remove_digito_verificador_puntos("2343234-K"))

    def test_digito_verificador(self):
        self.assertEqual(2, digito_verificador("12456371"))
        self.assertEqual(4, digito_verificador("6786532"))
        self.assertEqual(8, digito_verificador("6786530"))
        self.assertEqual(1, digito_verificador("6786539"))
        self.assertEqual('k', digito_verificador("14123742"))
