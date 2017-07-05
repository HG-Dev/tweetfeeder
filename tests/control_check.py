"""
Tests the ability to change bot functionality while running
As with all tests, use python -m unittest tests/~~
so that the tweetfeeder module is found.
"""
import unittest
import json
from flags import Flags
from os import mkdir, path, remove
from tweetfeeder import TweetFeederBot
from tweetfeeder.exceptions import LoadConfigError
from tweetfeeder.flags import BotFunctions
from tweetfeeder.logs import Log
from tweetfeeder.file_io.config import Config
from tweetfeeder.file_io.utils import FileIO

# pylint: disable=W0612

class TFControlTests(unittest.TestCase):
    """
    Test the ability to control bot functionality,
    particularly through the MasterControl object.
    """
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
        bot = TweetFeederBot(BotFunctions.Log, "tests/config/test_settings.json")
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