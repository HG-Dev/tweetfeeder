"""
Tests the ability to change bot functionality while running
As with all tests, use python -m unittest tests/~~
so that the tweetfeeder module is found.
"""
import unittest
import json
from os import mkdir, path, remove
from datetime import datetime, timedelta
from flags import Flags
from tweetfeeder import TweetFeederBot
from tweetfeeder.exceptions import TweetFeederError
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log
from tweetfeeder.file_io.config import Config
from tweetfeeder.file_io.utils import FileIO
from tweetfeeder.file_io.models import Stats

# pylint: disable=W0612

class TFControlTests(unittest.TestCase):
    """
    Test the ability to control bot functionality,
    particularly through the MasterControl object.
    """
    @classmethod
    def setUpClass(cls):
        """
        Ensures a place for Log output to go.
        """
        try:
            mkdir("tests/__temp_output__")
        except FileExistsError:
            pass

        logging_unifier = TweetFeederBot()

        cls.log_buffer = Log.DebugStream()
        Log.enable_debug_output(True, cls.log_buffer)
        Log.debug("setUpClass", "dbg")
        Log.info("setUpClass", "info")
        cls.assertTrue(cls, cls.log_buffer.has_all_text(['dbg', 'info']))
        cls.fresh_tweet_times = []

    def setUp(self):
        ''' Preparation for each test '''
        self.fresh_tweet_times = [
            datetime.now()+timedelta(minutes=1),
            datetime.now()+timedelta(minutes=2),
            datetime.now()+timedelta(minutes=3)
        ]

    def tearDown(self):
        """ Clears buffer """
        self.log_buffer.clear()

    def test_flag_adding(self):
        ''' Does adding and subtracting using BotFunctions work as expected? '''
        functions: BotFunctions = BotFunctions(BotFunctions.All)
        self.assertTrue(functions.SaveStats)
        functions = functions ^ BotFunctions.SaveStats
        self.assertTrue(functions.Tweet)
        self.assertFalse(functions.SaveStats)
        functions = functions | BotFunctions.SaveStats
        self.assertTrue(functions.SaveStats)
        functions = functions ^ BotFunctions("SaveStats")
        self.assertTrue(functions.Log)
        self.assertFalse(functions.SaveStats)
        functions = functions | BotFunctions("SaveStats")
        self.assertTrue(functions.SaveStats)

    def test_bad_flag(self):
        ''' Does BotFunctions handle improper inits correctly? '''
        self.assertTrue(BotFunctions("SaveStats").SaveStats)
        with self.assertRaises(ValueError):
            flag = BotFunctions("savestats")
        with self.assertRaises(ValueError):
            flag = BotFunctions("sdlaasfasdf")

    def test_add_rem_function(self):
        """
        Does using the MasterCommand class to add or remove a function
        result in verifiable change within a running Bot?
        """
        bot = TweetFeederBot(BotFunctions(), "tests/config/test_settings.ini")
        bot.config.tweet_times = []
        try:
            remove(bot.config.stats_filepath)
        except FileNotFoundError:
            pass
        
        # Use cmd to start tweeting
        json_dict = FileIO.get_json_dict('tests/cassettes/stream_get_master_dm.json')
        json_dict['direct_message']['text'] = 'useless'
        bot.userstream.listener.on_data(json.dumps(json_dict))
        json_dict['direct_message']['text'] = 'functionality add tweet'
        bot.userstream.listener.on_data(json.dumps(json_dict))
        json_dict['direct_message']['text'] = 'functionality add Tweet'
        bot.userstream.listener.on_data(json.dumps(json_dict))
        self.assertTrue(bot.tweet_loop.is_running())
        json_dict['direct_message']['text'] = 'functionality remove Tweet'
        bot.tweet_loop.wait_for_tweet(60)
        bot.userstream.listener.on_data(json.dumps(json_dict))
        self.assertFalse(bot.tweet_loop.is_running())

    @unittest.skip("CMD loop not in use at the moment")
    def test_cmd_loop(self):
        """Does a TweetFeederBot behave normally when cmdloop is active?
        """
        bot = TweetFeederBot(BotFunctions.Tweet, "tests/config/test_auto_onetweet_settings.ini")
        bot.tweet_loop.wait_for_tweet(10)
        bot.shutdown()
        self.assertTrue(self.log_buffer.has_text("tweet"), self.log_buffer.buffer)
        self.log_buffer.clear()
        bot.stats.set_dirty()
        bot.refresh()
        print("Wait a few seconds, then type shutdown")
        bot.master_cmd.cmdloop()
        self.assertTrue(self.log_buffer.has_text("tweet"))

    @unittest.skip("Too slow")
    def test_force_tweet(self):
        """Can the TweetFeederBot be forced to tweet from the tweet feed?
        """
        bot = TweetFeederBot(BotFunctions(), "tests/config/test_settings.ini")
        self.assertEqual(bot.feed.total_tweets, 5)
        bot.config.tweet_times = self.fresh_tweet_times
        bot.config.functionality = BotFunctions.Tweet
        self.assertEqual(bot.feed.total_tweets, 5)
        bot.master_cmd.onecmd("tweet_now")
        self.assertTrue(self.log_buffer.has_text('DO_NOT_TWEET'), self.log_buffer.buffer)
        bot.tweet_loop.wait_for_tweet(3)
        bot.master_cmd.onecmd("tweet_now")
        bot.tweet_loop.wait_for_tweet(3)
        bot.master_cmd.onecmd("tweet_now")
        bot.tweet_loop.wait_for_tweet(3)
        bot.master_cmd.onecmd("tweet_now")
        bot.tweet_loop.wait_for_tweet(3)
        bot.master_cmd.onecmd("tweet_now")
        bot.shutdown()
        self.assertTrue(self.log_buffer.has_text('BROKEN_CHAIN'), self.log_buffer.buffer)

    def test_cmd_status(self):
        """Does the status command give info, and will it work correctly
        after tweet_now?
        """
        bot = TweetFeederBot(BotFunctions.Log, "tests/config/test_settings.ini")
        self.assertEqual(bot.feed.total_tweets, 5)
        bot.config.tweet_times = self.fresh_tweet_times
        bot.master_cmd.onecmd("status")
        # Status should show that the bot is largely inactive
        self.assertFalse(self.log_buffer.has_text('seconds'))
        bot.config.functionality = BotFunctions.Tweet
        bot.master_cmd.onecmd("status")
        # Status should show that the bot will tweet soon
        self.assertTrue(self.log_buffer.has_text('seconds'), self.log_buffer.buffer)
        bot.shutdown()


    @unittest.skip("Should be VCR'd, but passes for now")
    def test_sync_stats(self):
        """Does the sync_stats command safely synchronize feed stats?
        Might it need a cooldown timer so it doesn't look like it's spamming?"""
        bot = TweetFeederBot(BotFunctions(), "tests/config/test_settings.ini")
        bot.stats = Stats("tests/config/test_stats_real_excerpt.json")
        self.assertTrue(bot.stats.get_tweet_stats("SPLITTING_IMAGE")['favorites'] == 999)
        bot.master_cmd.onecmd("sync_stats")
        favs = (
            bot.stats.get_tweet_stats("SPLITTING_IMAGE")['favorites'],
            bot.stats.get_tweet_stats("SINGULARITY")['favorites'],
            bot.stats.get_tweet_stats("PAIN_TRAIN")['favorites']
        )
        self.assertFalse(favs[0] == 999)
        Log.info("sync_stats", "result: favs {} {} {}".format(*favs))
        bot.shutdown()

