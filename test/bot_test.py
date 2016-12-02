from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock

from test.model_interface_test import mock_model_interface
import pytz
from src.bot import update_cache_and_reply, is_a_proper_time

class TestStart(TestCase):

    def setUp(self):
        self.tl_id = 32
        self.rut = 73829172

    def createUser(self, telegram_id, rut):

        pass

    def testUpdateCacheAndReply(self):
        mock = MagicMock()
        with mock_model_interface():
            pass
            # We also need to mock the request query or "Web"
            #self.createUser(self.tl_id, self.rut)
            #update_cache_and_reply(self.tl_id, self.rut, mock, True)

    def testProperTime(self):
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 14, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 23, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 18, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 3, 00, 00)))

        self.assertFalse(is_a_proper_time(datetime(2016, 12, 4, 14, 00)))
        self.assertFalse(is_a_proper_time(datetime(2016, 12, 3, 14, 00)))
        self.assertFalse(is_a_proper_time(datetime(2016, 12, 2, 10, 00)))
        self.assertTrue(is_a_proper_time(datetime(2016, 12, 2, 10, 00, tzinfo=pytz.timezone("America/Santiago"))))


