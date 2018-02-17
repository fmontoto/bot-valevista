import codecs
import pathlib
import os
import unittest
from unittest import TestCase
import inspect

from src.utils import Rut
from src.messages import Messages
from src import web


class WebPageFromFileRetriever(web.WebRetriever):
    def setPath(self, path: str):
        self.path = path

    def retrieve(self, unused_rut: Rut):
        with codecs.open(self.path, "r", encoding='utf-8',
                         errors='ignore') as f:
            web = f.read()
        return web


def TestFilesBasePath() -> pathlib.Path:
        web_path = pathlib.Path(os.path.dirname(inspect.getfile(web)))
        return web_path.joinpath('test/test_pages')


class TestPublicParser(TestCase):
    def setUp(self):
        self.retriever = WebPageFromFileRetriever()
        self.base_path = TestFilesBasePath()
        self.dummy_rut = Rut.build_rut('12444333-3')

    def testClientePage(self):
        path = self.base_path.joinpath('cliente.html')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.CLIENTE, web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual(Messages.CLIENTE_ERROR, web_result.get_error())

    def testErrorPage(self):
        path = self.base_path.joinpath('Error.htm')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.INTENTE_NUEVAMENTE,
                         web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual(Messages.INTENTE_NUEVAMENTE_ERROR,
                         web_result.get_error())

    def testNadaPage(self):
        path = self.base_path.joinpath('no_pagos.html')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.NO_ERROR, web_result.get_type())
        self.assertEqual(0, len(web_result.get_events()))
        self.assertEqual('', web_result.get_error())

    def testDataPage(self):
        path = self.base_path.joinpath('pagado_rendido.html')
        self.retriever.setPath(path)
        raw_page = self.retriever.retrieve(self.dummy_rut)
        web_result = web.Parser.parse(raw_page)
        self.assertEqual(web.TypeOfWebResult.NO_ERROR, web_result.get_type())
        self.assertEqual(3, len(web_result.get_events()))
        self.assertEqual('', web_result.get_error())
        first_expected_str = (
                'Fecha de Pago: 28/10/2016\n'
                'Medio de Pago: Abono en Cuenta Corriente de Otros Bancos\n'
                'Oficina/Banco: BCO. CRED. E INVERSIONES\n'
                'Estado: Pagado / Rendido')
        self.assertEqual(first_expected_str,
                         web_result.get_events()[0].string_representation())


if __name__ == '__main__':
    unittest.main()
