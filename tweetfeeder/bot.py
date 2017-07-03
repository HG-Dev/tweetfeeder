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
        self.stats = Stats(self.config.stats_filepath, functionality.SaveStats)
        self.tweet_loop = TweetLoop(self.config, self.feed, self.stats)
        Log.enable_file_output(functionality.Log, self.config.log_filepath)
        Log.info("BOT.init", "{:-^80}".format(str(functionality)))

        # Follow up initialization
        self.userstream = Stream(
            self.config.authorization,
            TweetFeederListener(self.config, self.stats)
        )
        self.toggle_userstream(BotFunctions.Listen in functionality)

    def refresh(self):
        ''' Recreates some objects used by the bot with new functionality. '''
        self.shutdown()
        self.feed = Feed(self.config.feed_filepath)
        self.stats = Stats(self.config.stats_filepath, self.config.functionality.SaveStats)
        if self.config.functionality.Tweet:
            self.tweet_loop.start()
        self.toggle_userstream(self.config.functionality.Listen)
        Log.debug("BOT.refresh", "Current index: " + str(self.stats.last_feed_index))

    def toggle_userstream(self, enabled=True):
        ''' Enable stream listening '''
        if enabled:
            self.userstream.userstream(async=True)
        else:
            self.userstream.disconnect()

    def shutdown(self):
        ''' Stops stream tracking and other loops, presumably to end the program. '''
        Log.info("BOT.shutdown", "Stopping stream and loops.")
        self.toggle_userstream(False)
        self.tweet_loop.stop()
