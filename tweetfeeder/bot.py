"""
Handles the import of config data
and automatic usage of Twitter.
"""
from tweepy import API, Stream
from tweetfeeder.file_io import Config
from tweetfeeder.logs import Log
from tweetfeeder.flags import BotFunctions
from tweetfeeder.streaming import TweetFeederListener

class TweetFeederBot:
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
        self.tweet_thread = None
        #super(TweetFeederBot, self).__init__(self.api)
        Log.enable_file_output(
            BotFunctions.LogToFile in functionality,
            self.config.filenames['log']
        )
        Log.info("BOT.init", "{:-^80}".format(str(functionality)))

        # Follow up initialization
        self.userstream = Stream(
            self.config.authorization,
            TweetFeederListener(self.config, self.api)
        )
        self.toggle_userstream(BotFunctions.Listen in functionality)

    def toggle_userstream(self, enabled=True):
        ''' Enable stream listening '''
        if enabled:
            self.userstream.userstream(async=True)
        else:
            self.userstream.disconnect()
