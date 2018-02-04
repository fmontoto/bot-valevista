import os
from unittest import TestCase

from src import web


class TestRut(TestCase):
    def setUp(self):
        self.t = web.Web
        self.pages = [("test_pages/pagado_rendido.html", self.t.EXPECTED),
                      ("test_pages/cliente.html", self.t.CLIENTE),
                      ("test_pages/Error.htm", self.t.INTENTE_NUEVAMENTE),
                      ("test_pages/no_pagos.html", self.t.NO_PAGOS)]

    def tearDown(self):
        pass

    def testParsing(self):
        t = self.t("rut", "digito")
        for path, type in self.pages:
            try:
                t.load_page(path)
            except FileNotFoundError as e:
                t.load_page(os.path.join("test", path))
            t.parse()
            self.assertEqual(type, t.page_type)
