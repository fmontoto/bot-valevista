from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import models, model_interface
from src.model_interface import get_user_id, cached_result, update_cached_result



class TestModelInterface(TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        models.Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.old_session = model_interface.session
        model_interface.session = self.session

    def tearDown(self):
        model_interface.session = self.old_session

    def testGetUserId(self):
        self.assertRaises(ValueError, get_user_id, 2342, False)
        new_id = get_user_id(2342, True)
        self.assertEqual(new_id, get_user_id(2342, False))
        self.assertNotEqual(new_id, get_user_id(2351, True))
