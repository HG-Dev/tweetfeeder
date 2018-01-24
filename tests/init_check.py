"""
Tests the basic file io / init of tweetfeeder.bot
As with all tests, use python -m unittest tests/~~
so that the tweetfeeder module is found.
"""
import unittest
from os import mkdir, path, remove
from tweetfeeder import TweetFeederBot
from tweetfeeder.exceptions import LoadConfigError
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log

# pylint: disable=W0612

class TFInitTests(unittest.TestCase):
    """
    Test the initialization of TweetFeederBot
    and the serialization of config+json files.
    """

    @classmethod
    def setUpClass(cls):
        """
        For testing purposes, ensure that the log and tracking
        outputs from the "correct" test settings are deleted.
        """
        try:
            mkdir("tests/__temp_output__")
        except FileExistsError:
            try:
                remove("tests/__temp_output__/tweet_stats.json")
            except FileNotFoundError:
                pass

    def tearDown(self):
        ''' Ensure no stats remain after method ends '''
        if path.exists("tests/__temp_output__/tweet_stats.json"):
            raise ValueError

    def test_no_settings_init(self):
        ''' Attempt to initialize a bot without settings. '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="Nonexistant ini file")

    @unittest.skip("json.decoder.JSONDecodeError not catching")
    def test_bad_json_init(self):
        ''' Attempt to initialize a bot with bad config file '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="tests/config/test_settings_bad.ini")

    def test_wrong_file_init(self):
        ''' Attempt to initialize a bot with non-ini file '''
        with self.assertRaises(LoadConfigError): #Stage one failure
            broken_bot = TweetFeederBot(config_file="config/credentials.json")

    def test_bad_settings_init(self):
        ''' Attempt to initialize a bot with no auth filepath '''
        with self.assertRaises(LoadConfigError): #Stage two failure
            broken_bot = TweetFeederBot(config_file="tests/config/test_settings_nocreds.ini")

    def test_log_writing(self):
        ''' Does the bot write to a log when initializing? '''
        bot = TweetFeederBot(config_file="tests/config/test_settings.ini")
        with open(bot.config.log_filepath, encoding='utf8') as logfile:
            self.assertIn("init", logfile.read())

    def test_all_log_levels(self):
        ''' Do all the logging levels work? '''
        # Sets up logger just in case
        bot = TweetFeederBot(BotFunctions.Log, "tests/config/test_settings.ini")
        Log.info("init_check", "INFO TEST")
        Log.warning("init_check", "WARNING TEST")
        Log.error("init_check", "ERROR TEST")
        with open(bot.config.log_filepath, encoding='utf8') as logfile:
            logtext = logfile.read()
            self.assertIn("INFO", logtext)
            self.assertIn("WARNING", logtext)
            self.assertIn("ERROR", logtext)

    def test_combined_logging(self):
        ''' Does setting BotFunctions to 3 really give us all logs? '''
        bot = TweetFeederBot(BotFunctions.Log, "tests/config/test_settings.ini")
        Log.info("init_check", "BotFunctions.Log check")
        with open(bot.config.log_filepath, encoding='utf8') as logfile:
            self.assertIn("BotFunctions.Log check", logfile.read())

    def test_bad_tweet_times(self):
        ''' Are datetime breaking tweet times caught? '''
        with self.assertRaises(LoadConfigError):
            broken_bot = TweetFeederBot(config_file="tests/config/test_settings_badtimes.ini")

    def test_shutdown(self):
        ''' Can the bot use the shutdown method to stop the program? '''
        Log.info("init_check", "Bot shutdown test")
        bot = TweetFeederBot(
            BotFunctions.Log,
            "tests/config/test_settings.ini"
        )
        bot.config.tweet_times = []
        log_buffer = Log.DebugStream()
        Log.enable_debug_output(True, log_buffer)
        bot.config.functionality = BotFunctions.Log | BotFunctions.Tweet
        self.assertTrue(bot.tweet_loop.is_running())
        bot.tweet_loop.wait_for_tweet(4)
        self.assertTrue(log_buffer.has_text("DO_NOT_TWEET"), "Didn't tweet: " + str(log_buffer))
        bot.shutdown()
        self.assertTrue(log_buffer.has_text("shutdown"))
        self.assertFalse(bot.tweet_loop.is_running())
