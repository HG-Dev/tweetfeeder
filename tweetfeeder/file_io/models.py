''' Compile-time configuration data for hg_tweetfeeder.bot '''
import json
from shutil import copyfile
from .utils import FileIO
from .config import Config
from ..exceptions import LoadFeedError
from ..flags import BotFunctions
from ..logs import Log

class Feed:
    ''' On-demand data from tweet feed and stats. '''
    def __init__(self, config: Config):
        ''' Save filepaths for the feed and stats '''
        self._config = config
        self.total_tweets = 0
        self.current_index = self._get_last_index()
        self.index = 0

    def _get_last_index(self):
        ''' Loads the last tweeted index from the stats file if it exists '''
        try:
            stats = FileIO.get_json_dict(self._config.stats_filepath)
        except FileNotFoundError:
            return 0
        else:
            return stats['feed_index']

    def set_last_index(self, index):
        ''' Sets the last tweeted index in the stats file. '''
        self.current_index = index
        self._save_stats(index)

    def _save_stats(self, last_index=-1):
        """
        Creates a stats file, if necessary, to preserve the
        last tweeted index between sessions. TODO: Also save stats
        """
        # Prepare all_tweet_data; attempt to load existing data
        try:
            with open(self._config.stats_filepath, 'r', encoding='utf8') as infile:
                all_tweet_stats = json.load(infile)
        except FileNotFoundError:
            # Create default stats dictionary
            all_tweet_stats = {'feed_index': 0}
        else:
            # Save backup just in case: this is valuable data, after all
            copyfile(self._config.stats_filepath, self._config.stats_filepath + ".bak")

        #Edit all_tweet_stats
        if last_index >= 0:
            all_tweet_stats['feed_index'] = last_index
        # if BotFunctions.SaveTweetStats in self.functionality and tweet:
        #     if tweet.author.id == self.config.my_id: #Bot tweeted this
        #         all_tweet_stats['tweet_stats'][tweet.id]['title'] = tweet.title
        #Save all_tweet_data to config.filepaths['stats']
        if BotFunctions.SaveStats in self._config.functionality:
            Log.debug("models.save", "Saving stats to " + self._config.stats_filepath)
            FileIO.save_json_dict(self._config.stats_filepath, all_tweet_stats)

    def get_tweets(self, from_index: int):
        """
        Loads a tweet or chain of tweets at feed_index
        and returns them along with the total tweets available.
        """
        next_tweets = []
        index = from_index
        try:
            feed_data = FileIO.get_json_dict(self._config.feed_filepath)
        except FileNotFoundError:
            raise LoadFeedError(
                "Couldn't load feed at " + (self._config.feed_filepath or "(none given)")
            )
        else:
            self.total_tweets = len(feed_data)
            if index >= self.total_tweets:
                raise LoadFeedError(
                    "Given index is greater than total_tweets: " +
                    "{} from {}".format(index+1, self.total_tweets)
                )
            next_tweets.append(feed_data[index])
            itr = 0
            while feed_data[index+itr]['chain'] and index + itr + 1 < self.total_tweets:
                itr += 1
                next_tweets.append(feed_data[itr])

        return next_tweets
