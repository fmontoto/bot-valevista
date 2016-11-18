from unittest import TestCase

from src import web


class TestRut(TestCase):
    def setUp(self):
        self.t = web.Web
        self.pages = [ ("test/test_pages/pagado_rendido.html", self.t.EXPECTED)
                     , ("test/test_pages/cliente.html", self.t.CLIENTE)
                     , ("test/test_pages/no_pagos.html", self.t.NO_PAGOS)]

    def tearDown(self):
        pass

    def testParsing(self):
        t = self.t("rut", "digito")
        for path, type in self.pages:
            t.load_page(path)
            t.parse()
            self.assertEqual(type, t.page_type)
