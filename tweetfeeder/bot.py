"""
Handles the import of config data
and automatic usage of Twitter.
"""
from tweepy import API, StreamListener
from tweetfeeder.file_io import Config

class TweetFeederBot(StreamListener):
    """
    Dual-threaded bot for posting tweets periodically
    and tracking tweet performance / responses.
    Also takes commands from a master Twitter account.
    """
    def __init__(self, functionality, config_file="config.json"):
        """
        Create a TweetFeeder bot and acquire
        authorization from Twitter
        """
        # Load settings. This could raise a TweetFeeder error
        config = Config(config_file)
        self.config = config
        self.functionality = functionality
        self.api = API(config.authorization)
        super(TweetFeederBot, self).__init__(self.api)

