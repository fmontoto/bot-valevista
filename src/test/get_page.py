"""Test call for testing web retrieve, don't call automatically, as it does a
real http GET."""

import unittest
from unittest import TestCase

from src.utils import Rut
from src import web


class TestGetPage(TestCase):
    """Get a real page using dummy_rut."""
    def setUp(self):
        self.dummy_rut = Rut.build_rut('17325823-2')

    def test_client(self):
        """Simple get and parse the bank's page."""
        raw_page = web.WebPageDownloader().retrieve(self.dummy_rut)
        web.Parser.parse(raw_page)


if __name__ == '__main__':
    unittest.main()
