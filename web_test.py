from unittest import TestCase

import web


class TestRut(TestCase):
    def setUp(self):
        self.t = web.Web
        self.pages = [ ("test_pages/pagado_rendido.html", self.t.EXPECTED)
                     , ("test_pages/cliente.html", self.t.CLIENTE)
                     , ("test_pages/no_pagos.html", self.t.NO_PAGOS)]

    def tearDown(self):
        pass

    def testParsing(self):
        import os
        print (os.getcwd())
        t = self.t("rut", "digito")
        for path, type in self.pages:
            t.load_page(path)
            t.parse()
            self.assertEqual(type, t.page_type)
