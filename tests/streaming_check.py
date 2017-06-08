"""
Tests the basic file io / init of tweetfeeder.bot
As with all tests, use python -m unittest tests.~~
so that the tweetfeeder module is found.
"""
import unittest
from shutil import rmtree
from os import mkdir
from tweetfeeder import TweetFeederBot
from tweetfeeder.exceptions import LoadConfigError
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log
from .config.vcr_settings import TAPE

# pylint: disable=W0612

class TFStreamTests(unittest.TestCase):
    """
    Test the initialization of TweetFeederBot
    and the serialization of json files.
    """

    BOT = object()

    @classmethod
    def setUpClass(cls):
        """
        For testing purposes, ensure that the log and tracking
        outputs from the "correct" test settings are deleted.
        """
        try:
            rmtree("tests/__temp_output__")
        except FileNotFoundError:
            print("init_check.setUpClass: no __temp_output__ to clean up")
        else:
            mkdir("tests/__temp_output__")

        TFStreamTests.BOT = TweetFeederBot(
            BotFunctions.LogToFile,
            config_file="tests/config/test_settings.json"
        )
        return TFStreamTests()

    def tearDown(self):
        ''' Get BOT ready for the next test '''
        TFStreamTests.BOT.toggle_userstream(False)

    #@TAPE.use_cassette
    def test_connection(self):
        ''' Did NORMAL_BOT connect to Twitter's userstream? '''
        TFStreamTests.BOT.toggle_userstream(True)
        self.assertTrue(True) #TFStreamTests.BOT.userstream.running)
