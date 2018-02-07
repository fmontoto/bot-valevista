import pathlib
import os
import unittest
from unittest import TestCase

from src import web


class TestRut(TestCase):
    def setUp(self):
        #Ugly :(
        import inspect
        web_path = pathlib.Path(os.path.dirname(inspect.getfile(web)))
        base_path = web_path.joinpath('test/test_pages')
        self.t = web.Web
        self.pages = [(base_path.joinpath("pagado_rendido.html"), self.t.EXPECTED),
                      (base_path.joinpath("cliente.html"), self.t.CLIENTE),
                      (base_path.joinpath("Error.htm"), self.t.INTENTE_NUEVAMENTE),
                      (base_path.joinpath("no_pagos.html"), self.t.NO_PAGOS)]

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


if __name__ == '__main__':
    unittest.main()
