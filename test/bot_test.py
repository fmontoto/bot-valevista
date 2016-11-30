from unittest import TestCase
from unittest.mock import MagicMock

from test.model_interface_test import mock_model_interface
from src.bot import update_cache_and_reply

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


