"""
Tests the bot's reactions to events that
come from Twitter's userstream via Tweepy.
As with all tests, use python -m unittest tests
so that the tweetfeeder module is found.
"""
import unittest
from os import mkdir, remove, path
from time import time, sleep
from tweetfeeder import TweetFeederBot
from tweetfeeder.streaming import TweetFeederListener
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log
from vcr import VCR

TAPE = VCR(
    cassette_library_dir='tests/cassettes',
    filter_headers=['Authorization'],
    serializer='json',
    match_on=['host']
)

# pylint: disable=W0612

class TFStreamTests(unittest.TestCase):
    """
    Test the ability of TweetFeederBot, or more specifically,
    TweetFeederListener to sort events from Twitter.
    """
    @classmethod
    def setUpClass(cls):
        """
        For testing purposes, ensure that the log and tracking
        outputs from the "correct" test settings are deleted.
        Also prepares the Log singleton using a new TweetFeederBot.
        """
        try:
            mkdir("tests/__temp_output__")
        except FileExistsError:
            pass

        cls.bot = TweetFeederBot(
            BotFunctions.Log | BotFunctions.Listen,
            config_file="tests/config/test_settings.ini"
        )
        try:
            remove(cls.bot.config.stats_filepath)
        except FileNotFoundError:
            pass
        cls.log_buffer = Log.DebugStream()
        cls.listener = cls.bot.userstream.listener
        Log.enable_debug_output(True, cls.log_buffer)
        cls.assertTrue(cls.bot, "Shared bot isn't initialized")
        cls.bot.stats.register_tweet(100, 'STREAM_TEST')
        print(cls.bot.stats.data['id_to_title'])
        print(cls.bot.stats.data['tweets'])

    def tearDown(self):
        ''' Cleanup after each test '''
        self.log_buffer.buffer.clear()
        self.bot.userstream.disconnect()

    @classmethod
    def tearDownClass(cls):
        ''' Final cleanup '''
        cls.bot.shutdown()

    def test_connection_online(self):
        ''' Can NORMAL_BOT connect to Twitter's userstream? '''
        self.assertTrue(self.bot, "Shared bot isn't initialized")
        self.assertTrue(self.bot.userstream.running, "Wasn't running from the beginning")
        self.bot.toggle_userstream(True)
        self.assertTrue(self.bot.userstream.running)
        self.bot.toggle_userstream(False)

    def test_favorited(self):
        ''' Does the bot record "favorited" events? '''
        with open('tests/cassettes/stream_favorited.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('favorite'), "Favorite event not recorded")
            self.assertEqual(self.bot.stats.get_tweet_stats("STREAM_TEST")['favorites'], 1)

    def test_unfavorited(self):
        ''' Does the bot record "unfavorited" events? '''
        with open('tests/cassettes/stream_unfavorited.json', encoding='utf8') as cassette:
            ccount = self.bot.stats.get_tweet_stats("STREAM_TEST")['favorites']
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('unfavorite'), "Unfavorite event not recorded")
            self.assertEqual(self.bot.stats.get_tweet_stats("STREAM_TEST")['favorites'], 0)

    def test_followed(self):
        ''' Does the bot ignore "followed" events? '''
        with open('tests/cassettes/stream_followed.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(self.log_buffer.has_text(), "Buffer should be empty!")

    def test_get_reply(self):
        """
        Test replies to bot account's tweets.
        The given JSON, unfortunately, contains no information as to whether
        the reply is part of a discussion thread.
        """
        ccount = self.bot.stats.get_tweet_stats("STREAM_TEST")['replies']
        with open('tests/cassettes/stream_get_reply_thread.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('reply'), "Reply event not recorded")
        with open('tests/cassettes/stream_get_reply.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('reply'), "Reply event not recorded")
        self.assertEqual(self.bot.stats.get_tweet_stats("STREAM_TEST")['favorites'], ccount+1)

    def test_mentions_and_timeline(self):
        ''' Does the bot ignore mere mentions and Tweets from followed users? '''
        with open('tests/cassettes/stream_mentioned.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(self.log_buffer.has_text(), "Buffer should be empty!")
        with open('tests/cassettes/stream_timeline_status.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(self.log_buffer.has_text(), "Buffer should be empty!")

    def test_retweeted(self):
        ''' Does the bot record retweet events? '''
        with open('tests/cassettes/stream_retweeted.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('retweet'), "Retweet event not recorded")
            self.listener.cancel_checks()
        self.assertEqual(self.bot.stats.get_tweet_stats("STREAM_TEST")['retweets'], 1)

    def test_quote_retweeted(self):
        ''' Does the bot record quote retweet events? '''
        ccount = self.bot.stats.get_tweet_stats("STREAM_TEST")['requotes']
        with open('tests/cassettes/stream_quoteretweeted.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text('quote'), "Quote event not recorded")
        self.assertEqual(self.bot.stats.get_tweet_stats("STREAM_TEST")['requotes'], ccount+1)

    def test_publish(self):
        ''' Does the bot record the discovery of its own published tweet? '''
        with open('tests/cassettes/stream_send_public_tweet.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(
                self.log_buffer.has_text('tweet confirmed'),
                "Tweet publish event not recorded"
            )

    def test_send_reply(self):
        ''' Does the bot ignore its own replies to people? '''
        with open('tests/cassettes/stream_send_reply.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(self.log_buffer.has_text(), "Buffer should be empty!")

    def test_get_master_dm(self):
        ''' Does the bot respond to a DM from the master account? '''
        with open('tests/cassettes/stream_get_master_dm.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(self.log_buffer.has_text("CMD.status"))
    
    @TAPE.use_cassette("test_rt_comment_check.json")
    def test_rt_comment_check(self):
        ''' Does the check_for_tweets method discover and record RT comments? '''
        self.bot.userstream.listener.check_for_comments(100, self.bot.config.master_id)
        self.assertTrue(self.bot.stats.get_tweet_stats(100)['rt_comments'])
