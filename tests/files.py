"""
Setup for unit tests.abs
As with all tests, use python -m unittest tests.~~
so that the tweetfeeder module is found.
"""
import unittest
from tweetfeeder import TweetFeederBot
from tweetfeeder.exceptions import LoadConfigError

# pylint: disable=W0612

class TweetfeederTestCase(unittest.TestCase):
    """
    Test the initialization of TweetFeederBot
    and the serialization of json files.
    """
    def setUp(self):
        self.bot = TweetFeederBot(functionality=None, config_file="tests/config/test_settings.json")

    def test_no_settings_init(self):
        ''' Attempt to initialize a bot without settings. '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(None, "Nonexistant JSON file")

    def test_bad_json_init(self):
        ''' Attempt to initialize a bot with bad JSON '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(None, "tests/config/test_settings_bad.json")

    def test_wrong_file_init(self):
        ''' Attempt to initialize a bot with readable, but wrong JSON '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(None, "config/credentials.json")

    def test_bad_settings_init(self):
        ''' Attempt to initialize a bot with no auth filepath '''
        with self.assertRaises(LoadConfigError): #Stage two failure
            broken_bot = TweetFeederBot(None, "tests/config/test_settings_nocreds.json")

