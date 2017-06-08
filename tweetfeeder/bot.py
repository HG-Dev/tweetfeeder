"""
Handles the import of config data
and automatic usage of Twitter.
"""
from tweepy import API, StreamListener
from tweetfeeder.file_io import Config
from tweetfeeder.logs import Log
from tweetfeeder.flags import BotFunctions
from tweetfeeder.exceptions import LoadConfigError

class TweetFeederBot(StreamListener):
    """
    Dual-threaded bot for posting tweets periodically
    and tracking tweet performance / responses.
    Also takes commands from a master Twitter account.
    """
    def __init__(self, functionality=BotFunctions(), config_file="config.json"):
        """
        Create a TweetFeeder bot and acquire
        authorization from Twitter
        """
        Log.setup(type(self).__name__)
        Log.enable_console_output(BotFunctions.LogToConsole in functionality)
        self.config = Config(config_file)
        self.api = API(self.config.authorization)
        super(TweetFeederBot, self).__init__(self.api)
        Log.enable_file_output(
            BotFunctions.LogToFile in functionality,
            self.config.filenames['log']
        )
        # Other initialization unrelated to config
        Log.info("bot.init", "{:-^80}".format(str(functionality)))
        self.functionality = functionality


