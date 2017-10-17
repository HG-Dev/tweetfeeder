"""
Handles the import of config data
and automatic usage of Twitter.
"""
import cmd
from tweepy import Stream, API
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
        if enabled and not self.userstream.running:
            self.userstream.userstream(async=True)
        elif not enabled:
            self.userstream.disconnect()

    def alert_master(self, text):
        ''' Send a DM to the master account. '''
        self.tweet_loop.api.send_direct_message(user_id=self.config.master_id, text=text)

    def shutdown(self):
        ''' Stops stream tracking and other loops, presumably to end the program. '''
        Log.info("BOT.shutdown", "Stopping stream and loops.")
        self.toggle_userstream(False)
        self.tweet_loop.stop()
        return True

    class MasterCommand(cmd.Cmd):
        ''' Takes input to manipulate the Bot remotely. Only onecmd is being used at present. '''
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

        def do_sync_stats(self, args):
            """Runs through the entirety of registered tweets to ensure
            their stats are correct and up-to-date.

            TODO: Make this work for requotes/replies, too
            """
            api = API(self.bot.config.authorization)
            stats = self.bot.stats
            if not (api and stats):
                Log.error("BOT.cmd.sync_stats", "Cannot sync stats: bot lacks stats Functionality")
                return False

            processed = []
            for twid in stats.data['id_to_title']:
                title = stats.data['id_to_title'][twid]
                # Get status info from Twitter
                status = api.get_status(twid)
                if title not in processed:
                    # Overwrite numeric stats
                    processed.append(title)
                    stats.update_tweet_stats_from_status(status.__dict__)
                else:
                    # Mod numeric stats
                    stats.add_tweet_stats_from_status(status.__dict__)

        def do_status(self, args):
            """Returns information on the bot's status.
            """
            report = "Functions: {}\n".format(str(self.bot.config.functionality))
            report += "Feed index: {}\n".format(self.bot.tweet_loop.current_index)
            if self.bot.config.functionality.Tweet:
                report += "Time until next tweet: {} seconds".format(
                        self.bot.tweet_loop.time_until_tweet()
                    )
            
            Log.info(
                "CMD.status",
                report
            )

