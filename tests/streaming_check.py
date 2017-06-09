"""
Tests the bot's reactions to events that
come from Twitter's userstream via Tweepy.
As with all tests, use python -m unittest tests
so that the tweetfeeder module is found.
"""
import unittest
from shutil import rmtree
from os import mkdir
from tweetfeeder import TweetFeederBot
from tweetfeeder.streaming import TweetFeederListener
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log

# pylint: disable=W0612

class TFStreamTests(unittest.TestCase):
    """
    Test the initialization of TweetFeederBot
    and the serialization of json files.
    """
    @classmethod
    def setUpClass(cls):
        """
        For testing purposes, ensure that the log and tracking
        outputs from the "correct" test settings are deleted.
        Also prepares the Log singleton using a new TweetFeederBot.
        """
        try:
            rmtree("tests/__temp_output__")
        except FileNotFoundError:
            print("init_check.setUpClass: no __temp_output__ to clean up")
        else:
            mkdir("tests/__temp_output__")
        finally:
            print("setUpClass: Defining attributes")
            cls.bot = TweetFeederBot(
                BotFunctions.Log,
                config_file="tests/config/test_settings.json"
            )
            #cls.logger = Log.get_logger()
            cls.listener = TweetFeederListener(cls.bot.config, cls.bot.api)
            Log.enable_debug_output(True)
            cls.assertTrue(cls.bot, "Shared bot isn't initialized")

    def tearDown(self):
        ''' Cleanup after each test '''
        Log.clear_debug_buffer()

    def test_connection_online(self):
        ''' Can NORMAL_BOT connect to Twitter's userstream? '''
        self.assertTrue(self.bot, "Shared bot isn't initialized")
        self.bot.toggle_userstream(True)
        self.assertTrue(self.bot.userstream.running)
        self.bot.toggle_userstream(False)

    def test_favorited(self):
        ''' Does the bot record "favorited" events? '''
        with open('tests/cassettes/stream_favorited.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(Log.is_text_in_debug_buffer('favorite'), "Favorite event not recorded")

    def test_unfavorited(self):
        ''' Does the bot ignore "unfavorited" events? '''
        with open('tests/cassettes/stream_unfavorited.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(Log.is_text_in_debug_buffer(), "Buffer should be empty!")

    def test_followed(self):
        ''' Does the bot ignore "followed" events? '''
        with open('tests/cassettes/stream_followed.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(Log.is_text_in_debug_buffer(), "Buffer should be empty!")

    def test_get_reply(self):
        """
        Test replies to bot account's tweets.
        The given JSON, unfortunately, contains no information as to whether
        the reply is part of a discussion thread.
        """
        with open('tests/cassettes/stream_get_reply_thread.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(Log.is_text_in_debug_buffer('reply'), "Reply event not recorded")
        with open('tests/cassettes/stream_get_reply.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(Log.is_text_in_debug_buffer('reply'), "Reply event not recorded")

    def test_mentions_and_timeline(self):
        ''' Does the bot ignore mere mentions and Tweets from followed users? '''
        with open('tests/cassettes/stream_mentioned.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(Log.is_text_in_debug_buffer(), "Buffer should be empty!")
        with open('tests/cassettes/stream_timeline_status.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(Log.is_text_in_debug_buffer(), "Buffer should be empty!")

    def test_retweeted(self):
        ''' Does the bot record retweet events? '''
        with open('tests/cassettes/stream_retweeted.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(Log.is_text_in_debug_buffer('retweet'), "Retweet event not recorded")

    def test_quote_retweeted(self):
        ''' Does the bot record quote retweet events? '''
        with open('tests/cassettes/stream_quoteretweeted.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(Log.is_text_in_debug_buffer('quote'), "Quote event not recorded")

    def test_publish(self):
        ''' Does the bot record the discovery of its own published tweet? '''
        with open('tests/cassettes/stream_send_public_tweet.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertTrue(
                Log.is_text_in_debug_buffer('tweet confirmed'),
                "Tweet publish event not recorded"
            )

    def test_send_reply(self):
        ''' Does the bot ignore its own replies to people? '''
        with open('tests/cassettes/stream_send_reply.json', encoding='utf8') as cassette:
            self.listener.on_data(cassette.read())
            self.assertFalse(Log.is_text_in_debug_buffer(), "Buffer should be empty!")