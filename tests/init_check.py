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

# pylint: disable=W0612

class TweetFeederTestCase(unittest.TestCase):
    """
    Test the initialization of TweetFeederBot
    and the serialization of json files.
    """
    NORMAL_BOT = object()

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
        finally:
            mkdir("tests/__temp_output__")
        return TweetFeederTestCase()

    def test_no_settings_init(self):
        ''' Attempt to initialize a bot without settings. '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="Nonexistant JSON file")

    def test_bad_json_init(self):
        ''' Attempt to initialize a bot with bad JSON '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="tests/config/test_settings_bad.json")

    def test_wrong_file_init(self):
        ''' Attempt to initialize a bot with readable, but wrong JSON '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="config/credentials.json")

    def test_bad_settings_init(self):
        ''' Attempt to initialize a bot with no auth filepath '''
        with self.assertRaises(LoadConfigError): #Stage two failure
            broken_bot = TweetFeederBot(config_file="tests/config/test_settings_nocreds.json")

    def test_log_writing(self):
        ''' Does the bot write to a log when initializing? '''
        bot = TweetFeederBot(BotFunctions.LogToFile, "tests/config/test_settings.json")
        with open(bot.config.filenames['log']) as logfile:
            self.assertIn("bot.init", logfile.read())

    def test_all_log_levels(self):
        ''' Do all the logging levels work? '''
        # Sets up logger just in case
        bot = TweetFeederBot(BotFunctions.LogToFile, "tests/config/test_settings.json")
        Log.info("init_check","INFO TEST")
        Log.warning("init_check","WARNING TEST")
        Log.error("init_check","ERROR TEST")
        with open(bot.config.filenames['log']) as logfile:
            logtext = logfile.read()
            self.assertIn("INFO", logtext)
            self.assertIn("WARNING", logtext)
            self.assertIn("ERROR", logtext)

    def test_botfunctions_normal_logging(self):
        ''' Does setting BotFunctions to 3 really give us all logs? '''
        bot = TweetFeederBot(BotFunctions.Log, "tests/config/test_settings.json")
        Log.info("init_check", "BotFunctions.Log check")
        with open(bot.config.filenames['log']) as logfile:
            self.assertIn("BotFunctions.Log check", logfile.read())

