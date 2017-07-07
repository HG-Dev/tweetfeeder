"""
Handles the import of config data
and automatic usage of Twitter.
"""
import cmd
from tweepy import Stream
from tweetfeeder.file_io import Config
from tweetfeeder.logs import Log
from tweetfeeder.flags import BotFunctions
from tweetfeeder.streaming import TweetFeederListener
from tweetfeeder.tweeting import TweetLoop
from tweetfeeder.file_io.models import Feed, Stats
from tweetfeeder.exceptions import InvalidCommand

class TweetFeederBot:
    """
    Dual-threaded bot for posting tweets periodically
    and tracking tweet performance / responses.
    Also takes commands from a master Twitter account.
    """
    def __init__(self, functionality=BotFunctions(), config_file=None):
        """
        Create a TweetFeeder bot and acquire
        authorization from Twitter
        """
        Log.setup(type(self).__name__)
        Log.enable_console_output()
        Log.info("BOT.init", "{:-^80}".format(str(functionality)))
        self.config = Config(functionality, self.refresh, config_file)
        self.feed = Feed(self.config.feed_filepath)
        self.stats = Stats(self.config.stats_filepath, self.config.functionality.SaveStats)
        self.tweet_loop = TweetLoop(self.config, self.feed, self.stats)
        self.master_cmd = TweetFeederBot.MasterCommand(self)
        Log.enable_file_output(self.config.functionality.Log, self.config.log_filepath)
        Log.enable_dm_output(self.config.functionality.Alerts, self.alert_master)

        # Follow up initialization
        self.userstream = Stream(
            self.config.authorization,
            TweetFeederListener(self.config, self.stats, self.master_cmd.onecmd)
        )
        self.toggle_userstream(BotFunctions.Listen in functionality)

    def refresh(self):
        ''' Recreates some objects used by the bot with new functionality. '''
        Log.debug("BOT.refresh", "Current index: " + str(self.stats.last_feed_index))
        self.shutdown()
        self.feed = Feed(self.config.feed_filepath)
        self.stats = Stats(self.config.stats_filepath, self.config.functionality.SaveStats)
        if self.config.functionality.Tweet:
            self.tweet_loop.start()
        self.toggle_userstream(self.config.functionality.Listen)
        Log.enable_file_output(self.config.functionality.Log, self.config.log_filepath)
        Log.enable_dm_output(self.config.functionality.Alerts, self.alert_master)

    def toggle_userstream(self, enabled=True):
        ''' Enable stream listening '''
        if enabled:
            self.userstream.userstream(async=True)
        else:
            self.userstream.disconnect()

    def alert_master(self, text):
        ''' Send a DM to the master account. '''
        self.tweet_loop.api.send_direct_message(user_id=self.config.master_id, text=text)

    def shutdown(self):
        ''' Stops stream tracking and other loops, presumably to end the program. '''
        Log.info("BOT.shutdown", "Stopping stream and loops.")
        self.toggle_userstream(False)
        self.tweet_loop.stop()

    class MasterCommand(cmd.Cmd):
        ''' Takes input to manipulate the Bot remotely. '''
        def __init__(self, bot_self):
            ''' Establishes link to bot '''
            super(TweetFeederBot.MasterCommand, self).__init__(self)
            self.bot = bot_self
       
        def do_shutdown(self, args):
            ''' Shuts down the bot '''
            self.bot.shutdown()
            return True # Exits cmdloop

        def do_functionality(self, args):
            ''' Adds or removes a given function. '''
            addrem, function = tuple(args.split())
            mod_func = BotFunctions()
            try:
                mod_func = BotFunctions(function)
            except ValueError as e:
                raise InvalidCommand("Check BotFunction name") from e

            ar_code = addrem.lower()[0]
            if ar_code == 'a':
                self.bot.config.functionality = self.bot.config.functionality | mod_func
            elif ar_code == 'r':
                self.bot.config.functionality = self.bot.config.functionality ^ mod_func
            else:
                raise InvalidCommand("First argument should be 'add' or 'remove'.")

        def do_tweet_now(self, args):
            """Forces the current tweet loop timer to end immediately,
            ignoring tweet times.
            """
            self.bot.tweet_loop.force_tweet()