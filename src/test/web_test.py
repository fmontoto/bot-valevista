import codecs
import pathlib
import os
import unittest
from unittest import TestCase
import inspect

from src.utils import Rut
from src import web


class WebPageFromFileRetriever(web.WebRetriever):
    def setPath(self, path: str):
        self.path = path

    def retrieve(self, unused_rut: Rut):
        with codecs.open(self.path, "r", encoding='utf-8', errors='ignore') as f:
            web = f.read()
        return web


class TestParser(TestCase):
    def setUp(self):
        self.retriever = WebPageFromFileRetriever()
        #Ugly :(
        web_path = pathlib.Path(os.path.dirname(inspect.getfile(web)))
        self.base_path = web_path.joinpath('test/test_pages')
        self.dummy_rut = Rut.build_rut('12444333-3')

    def testClientePage(self):
        path = self.base_path.joinpath('cliente.html')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.CLIENTE, web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual(web.WebResult._CLIENTE_ERROR, web_result.get_error())

    def testErrorPage(self):
        path = self.base_path.joinpath('Error.htm')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.INTENTE_NUEVAMENTE,
                         web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual(web.WebResult._INTENTE_NUEVAMENTE_ERROR,
                         web_result.get_error())

    def testNadaPage(self):
        path = self.base_path.joinpath('no_pagos.html')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.NO_ERROR, web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual('', web_result.get_error())


class TaestRut(TestCase):
    def setUp(self):
        #Ugly :(
        web_path = pathlib.Path(os.path.dirname(inspect.getfile(web)))
        base_path = web_path.joinpath('test/test_pages')
        self.t = web.Web
        self.pages = [(base_path.joinpath("pagado_rendido.html"), self.t.EXPECTED),
                      (base_path.joinpath("cliente.html"), self.t.CLIENTE),
                      (base_path.joinpath("Error.htm"), self.t.INTENTE_NUEVAMENTE),
                      (base_path.joinpath("no_pagos.html"), self.t.NO_PAGOS)]

    def tearDown(self):
        pass

    def taestParsing(self):
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
