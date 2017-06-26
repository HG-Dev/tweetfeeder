"""
Handles the import of config data
and automatic usage of Twitter.
"""
from tweepy import API, Stream
from tweetfeeder.file_io import Config
from tweetfeeder.logs import Log
from tweetfeeder.flags import BotFunctions
from tweetfeeder.streaming import TweetFeederListener
from tweetfeeder.tweeting import TweetLoop
from tweetfeeder.file_io.models import Feed, Stats

class TweetFeederBot:
    """
    Dual-threaded bot for posting tweets periodically
    and tracking tweet performance / responses.
    Also takes commands from a master Twitter account.
    """
    def __init__(self, functionality=BotFunctions(), config_file="config.json", config_obj=None):
        """
        Create a TweetFeeder bot and acquire
        authorization from Twitter
        """
        Log.setup(type(self).__name__)
        Log.enable_console_output()
        self.config = config_obj or Config(functionality, self.refresh, config_file)
        self.feed = Feed(self.config.feed_filepath)
        self.stats = Stats(self.config.stats_filepath, lambda: functionality.SaveStats)
        self.tweet_loop = TweetLoop(self.config, self.feed, self.stats, functionality.Tweet)
        Log.enable_file_output(functionality.Log, self.config.log_filepath)
        Log.info("BOT.init", "{:-^80}".format(str(functionality)))

        # Follow up initialization
        self.userstream = Stream(
            self.config.authorization,
            TweetFeederListener(self.config, API(self.config.authorization))
        )
        self.toggle_userstream(BotFunctions.Listen in functionality)

    def refresh(self):
        ''' Recreates some objects used by the bot with new functionality. '''
        self.feed = Feed(self.config.feed_filepath)
        self.stats = Stats(self.config.stats_filepath, self.config.functionality.SaveStats)
        Log.debug("BOT.refresh", "Current index: " + str(self.stats.last_feed_index))

    def toggle_userstream(self, enabled=True):
        ''' Enable stream listening '''
        if enabled:
            self.userstream.userstream(async=True)
        else:
            self.userstream.disconnect()
