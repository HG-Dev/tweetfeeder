"""
Testing of the "tweeting" module
python -m unittest tests/tweeting_check.py

"""
import unittest
from os import mkdir
from os import remove
from os import path
from time import sleep
from vcr import VCR
from datetime import timedelta, datetime
from tweetfeeder import TweetFeederBot
from tweetfeeder.logs import Log
from tweetfeeder.flags import BotFunctions
from tweetfeeder.tweeting import TweetLoop
from tweetfeeder.exceptions import NoTimerError

TAPE = VCR(
    cassette_library_dir='tests/cassettes',
    filter_headers=['Authorization'],
    serializer='json',
    match_on=['host']
)

class TFTweetingTests(unittest.TestCase):
    """
    Test the ability of TweetFeederBot to make
    timed tweets under a variety of circumstances.
    """
    DEFAULT_STATS = "tests/__temp_output__/tweet_stats.json"
    @classmethod
    def setUpClass(cls):
        """
        Ensures a place for Log output to go.
        """
        cls.bot = TweetFeederBot(
            BotFunctions.Log,
            config_file="tests/config/test_settings.json"
        )

        try:
            mkdir("tests/__temp_output__")
        except FileExistsError:
            pass

        cls.log_buffer = Log.DebugStream()
        Log.enable_debug_output(True, cls.log_buffer)

    def setUp(self):
        ''' Preparation for each test '''
        self.bot.config.functionality = (
            BotFunctions.Log | BotFunctions.Tweet | BotFunctions.SaveStats
        )
        try:
            self.bot.config._filepaths['stats'] = TFTweetingTests.DEFAULT_STATS
            remove(self.bot.config.stats_filepath)
        except FileNotFoundError:
            pass
        else:
            Log.info("tweeting_check.setup", TFTweetingTests.DEFAULT_STATS + " deleted")
        self.bot.config.tweet_times = [
            datetime.now()+timedelta(minutes=1),
            datetime.now()+timedelta(minutes=2),
            datetime.now()+timedelta(minutes=3)
        ]
        self.bot.tweet_loop.feed.current_index = 0

    def tearDown(self):
        ''' Cleanup after each test '''
        self.log_buffer.buffer.clear()

    def test_false_start(self):
        ''' Will the TweetLoop start automatically regardless of auto_start? '''
        Log.info("tweeting_check", "false_start")
        self.assertFalse(self.bot.tweet_loop.is_running())
        with self.assertRaises(NoTimerError):
            self.bot.tweet_loop.stop()

    def test_stop_timer(self):
        ''' Will a cancelled timer avoid invoking a tweet, as it should? '''
        Log.info("tweeting_check", "stop_timer")
        self.bot.config._filepaths['feed'] = "tests/config/test_feed_singular.json"
        self.bot.config.tweet_times = []
        timer = TweetLoop(self.bot.config, None)
        timer.stop()
        sleep(4)
        self.assertFalse(
            self.log_buffer.has_text('TEST_ONE_TWEET'),
            "Did not prevent the tweeting of TEST_ONE_TWEET: " + str(self.log_buffer.buffer)
        )

    def test_one_tweet(self):
        ''' Can the TweetLoop class tweet one timed event? '''
        Log.info("tweeting_check", "one_tweet")
        self.bot.config._filepaths['feed'] = "tests/config/test_feed_singular.json"
        timer = TweetLoop(self.bot.config, None)
        timer.wait_for_tweet()
        self.assertTrue(
            self.log_buffer.has_text('TEST_ONE_TWEET'),
            "Did not tweet required text: " + str(self.log_buffer.buffer)
        )

    def test_chain_tweet(self):
        ''' Can the TweetLoop tweet a chain of tweets? '''
        Log.info("tweeting_check", "chain_tweet")
        self.bot.config._filepaths['feed'] = "tests/config/test_feed_multiple.json"
        self.bot.config._filepaths['stats'] = "tests/config/skip_first_tweet_stats.json"
        self.bot.config.functionality = BotFunctions.Log | BotFunctions.Tweet
        self.bot.config.tweet_times = []
        timer = TweetLoop(self.bot.config, None)
        timer.wait_for_tweet()
        self.assertFalse(
            self.log_buffer.has_text('DO_NOT_TWEET'),
            "Test chain is expected to use skip_first_tweet_stats to go straight to the chain."
        )
        self.assertTrue(
            self.log_buffer.has_text('3 tweets starting at 2 (CHAIN_1)'),
            "Tweet chain was not loaded/tweeted properly."
        )

    def test_resume_session(self):
        """
        Can the TweetLoop use tweet_stats to
        resume after a sudden halt?
        """
        Log.info("tweeting_check", "resume_session")
        self.assertTrue(BotFunctions.SaveStats in self.bot.config.functionality)
        self.bot.config._filepaths['feed'] = "tests/config/test_feed_multiple.json"
        self.bot.config.tweet_times = []
        timer = TweetLoop(self.bot.config, None, False)
        self.assertFalse(timer.is_running())
        timer.start()
        self.assertTrue(timer.feed.current_index == 0)
        timer.wait_for_tweet() # Wait for first tweet
        self.assertFalse(
            self.log_buffer.has_text('3 tweets starting at 2 (CHAIN_1)'),
            "Only one tweet should have been tweeted so far."
        )
        timer.wait_for_tweet(0.1) # Wait one second into the next
        timer.stop()
        Log.debug("tweeting_check", "CHECKING RESULT")
        self.assertFalse(
            self.log_buffer.has_text('3 tweets starting at 2 (CHAIN_1)'),
            "Loop should have been stopped before reaching chain.\n" + str(self.log_buffer.buffer)
        )
        self.assertTrue(
            path.exists(self.bot.config.stats_filepath), "Stats not created"
        )
        timer.start()
        timer.wait_for_tweet()
        self.assertTrue(
            self.log_buffer.has_text('3 tweets starting at 2 (CHAIN_1)'),
            "Resuming did not make the tweet chain appear."
        )
        timer.stop()

    @TAPE.use_cassette("test_online_tweet.json")
    def test_online_tweet(self):
        ''' Can the TweetLoop use the Tweepy API? '''
        config = self.bot.config
        config._filepaths['feed'] = "tests/config/test_feed_online.json"
        self.assertTrue(self.bot.config.feed_filepath == config.feed_filepath) # Simple test
        config.functionality = BotFunctions.All
        config.tweet_times = []
        loop = TweetLoop(config, self.bot.api)
        loop.wait_for_tweet()
        self.assertTrue(
            self.bot.tweet_loop.feed.get_tweet_stats("DEV_GREETINGS"),
            "Couldn't find tweet stats using title"
        )
