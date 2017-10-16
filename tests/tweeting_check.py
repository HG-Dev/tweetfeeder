"""
Testing of the "tweeting" module
python -m unittest tests/tweeting_check.py

"""
import unittest
from os import mkdir
from os import remove
from os import path
from time import sleep
from datetime import timedelta, datetime
from vcr import VCR
from tweetfeeder import TweetFeederBot
from tweetfeeder.logs import Log
from tweetfeeder.exceptions import TweetFeederError
from tweetfeeder.file_io import Config
from tweetfeeder.file_io.models import Feed, Stats
from tweetfeeder.flags import BotFunctions
from tweetfeeder.tweeting import TweetLoop

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
        logging_unifier = TweetFeederBot()

        try:
            mkdir("tests/__temp_output__")
        except FileExistsError:
            pass

        cls.log_buffer = Log.DebugStream()
        Log.enable_debug_output(True, cls.log_buffer)
        cls.fresh_tweet_times = []
        cls.botless_config = Config(
            BotFunctions.Log | BotFunctions.Tweet,
            None,
            "tests/config/test_settings.json"
        )
        cls.botless_config.min_tweet_delay = 1

    def setUp(self):
        ''' Preparation for each test '''
        self.botless_config.tweet_times = []
        self.fresh_tweet_times = [
            datetime.now()+timedelta(minutes=1),
            datetime.now()+timedelta(minutes=2),
            datetime.now()+timedelta(minutes=3),
            datetime.now()+timedelta(minutes=4)
        ]

    def tearDown(self):
        ''' Cleanup after each test '''
        self.log_buffer.clear()
        try:
            remove(self.botless_config.stats_filepath)
        except FileNotFoundError:
            pass

    def test_stop_timer(self):
        ''' Will a cancelled timer avoid invoking a tweet, as it should? '''
        Log.info("tweeting_check", "stop_timer")
        feed = Feed("tests/config/test_feed_singular.json")
        loop = TweetLoop(self.botless_config, feed)
        loop.stop()
        self.assertFalse(loop.is_running())

    def test_double_start(self):
        """Is TweetLoop capable to double-starting if start is called
        immediately after an auto-start?
        """
        Log.info("tweeting_check", "double_start")
        feed = Feed("tests/config/test_feed_singular.json")
        loop = TweetLoop(self.botless_config, feed)
        loop.start()
        loop.wait_for_tweet(1)
        self.assertTrue(
            self.log_buffer.has_text_nonce('Loop is already running'),
            "Failed to prevent a TweetLoop double-start."
        )
        loop.stop()

    def test_one_tweet(self):
        ''' Can the TweetLoop class tweet one timed event? '''
        Log.info("tweeting_check", "one_tweet")
        feed = Feed("tests/config/test_feed_singular.json")
        #self.botless_config.tweet_times = self.fresh_tweet_times
        loop = TweetLoop(self.botless_config, feed)
        self.assertTrue(loop.is_running())
        self.assertEqual(loop.stats.last_feed_index, 0)
        loop.wait_for_tweet(60)
        loop.stop()
        self.assertTrue(
            self.log_buffer.has_text_nonce('TEST_ONE_TWEET'),
            "Did not tweet exactly once: " + str(self.log_buffer.buffer)
        )

    def test_chain_tweet(self):
        ''' Can the TweetLoop tweet a chain of tweets? '''
        Log.info("tweeting_check", "chain_tweet")
        feed = Feed("tests/config/test_feed_multiple.json")
        stats = Stats("tests/config/skip_first_tweet_stats.json")
        loop = TweetLoop(self.botless_config, feed, stats)
        loop.wait_for_tweet(60, last_timer=True)
        self.assertFalse(
            self.log_buffer.has_text('DO_NOT_TWEET'),
            "Test chain is expected to use skip_first_tweet_stats to go straight to the chain."
        )
        self.assertTrue(
            self.log_buffer.has_text('CHAIN_3'),
            "Tweet chain was not loaded/tweeted properly."
        )
        loop.stop()

    def test_resume_session(self):
        """
        Can the TweetLoop use tweet_stats to
        resume after a sudden halt?
        """
        Log.info("tweeting_check", "resume_session")
        feed = Feed("tests/config/test_feed_multiple.json")
        stats = Stats(self.botless_config.stats_filepath, True)
        loop = TweetLoop(self.botless_config, feed, stats)
        loop.wait_for_tweet(60) # Wait for first tweet
        self.assertFalse(
            self.log_buffer.has_text('CHAIN_1'),
            "Only one tweet should have been tweeted so far: " + str(self.log_buffer.buffer)
        )
        loop.stop()
        Log.debug("tweeting_check", "CHECKING RESULT")
        self.assertFalse(
            self.log_buffer.has_text('CHAIN_1'),
            "Loop should have been stopped before reaching chain.\n" + str(self.log_buffer.buffer)
        )
        self.assertTrue(
            path.exists(self.botless_config.stats_filepath), "Stats not created"
        )
        loop.start()
        loop.wait_for_tweet(60, last_timer=True)
        self.assertTrue(
            self.log_buffer.has_text('CHAIN_3'),
            "Resuming did not make the tweet chain appear."
        )
        loop.stop()
    
    def test_no_boolean_feed(self):
        ''' Does the compensation for missing booleans (particularly chain) in the feed work? '''
        feed = Feed("tests/config/test_feed_nobools.json")
        timer = TweetLoop(self.botless_config, feed)
        Log.info("check_no_bools", "Est. runtime: 8 seconds")
        timer.wait_for_tweet(8)
        timer.wait_for_tweet(8)
        timer.stop()
        self.assertTrue(
            self.log_buffer.has_text('BOOL_ABSENSE_2'),
            "An error likely occurred. Check the log."
        )

    def test_feed_loop(self):
        ''' Does the tweeting loop continue to loop when the end of the feed is reached? '''
        Log.info("check_no_bools", "Est. runtime: 8 seconds")
        feed = Feed("tests/config/test_feed_singular.json")
        timer = TweetLoop(self.botless_config, feed)
        timer.wait_for_tweet(8)
        timer.wait_for_tweet(8)
        timer.stop()
        self.assertTrue(
            self.log_buffer.has_text('TEST_ONE_TWEET'),
            "Did not tweet... at all"
        )
        self.assertFalse(
            self.log_buffer.has_text_nonce('TEST_ONE_TWEET'),
            "Did not tweet more than once: " + str(self.log_buffer.buffer)
        )

    def test_feed_loop_filter(self):
        ''' Does the tweeting loop skip rerunning tweets that didn't reach a given score? '''
        Log.info("check_feed_loop_filter", "Est. runtime: 12 seconds")
        feed = Feed("tests/config/test_feed_multiple.json")
        stats = Stats("tests/config/test_stats_with_registered_tweets.json")
        timer = TweetLoop(self.botless_config, feed, stats)
        timer.wait_for_tweet(8)
        timer.wait_for_tweet(8)
        timer.wait_for_tweet(8)
        timer.wait_for_tweet(8)
        timer.stop()
        print(self.log_buffer.buffer)


    @unittest.skip("VCR not working very well")
    @TAPE.use_cassette("test_online_tweet.json")
    def test_online_tweet(self):
        ''' Can the TweetLoop use the Tweepy API? '''
        feed = Feed("tests/config/test_feed_online.json")
        stats = Stats(self.botless_config.stats_filepath)
        self.botless_config.functionality = BotFunctions.All
        loop = TweetLoop(self.botless_config, feed, stats)
        loop.wait_for_tweet(60)
        sleep(1)
        self.assertTrue(
            stats.get_tweet_stats("ONLINE_TEST"),
            "Couldn't find tweet stats using title"
        )
