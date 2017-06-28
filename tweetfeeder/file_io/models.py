''' Compile-time configuration data for hg_tweetfeeder.bot '''
import json
from shutil import copyfile
from collections import namedtuple
from tweepy.models import Status
from .utils import FileIO
from ..exceptions import LoadFeedError, UnregisteredTweetError, AlreadyRegisteredTweetError
from ..flags import BotFunctions
from ..logs import Log

class Feed:
    ''' On-demand data from tweet feed. '''
    def __init__(self, filepath: str):
        ''' Save filepaths for the feed and stats '''
        self.filepath = filepath
        self._total_tweets = 0

    @property
    def total_tweets(self) -> int:
        ''' The total tweets in the feed as last recorded. '''
        return self._total_tweets

    def get_tweets(self, from_index: int):
        """
        Loads a tweet or chain of tweets at feed_index
        and returns them along with the total tweets available.
        """
        next_tweets = []
        index = from_index
        try:
            feed_data = FileIO.get_json_dict(self.filepath)
        except FileNotFoundError:
            raise LoadFeedError(
                "Couldn't load feed at " + (self.filepath or "(none given)")
                )
        else:
            self._total_tweets = len(feed_data)
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

class Stats:
    ''' Access to Tweet stats and session data '''

    def __init__(self, filepath: str = "", save: bool = False):
        ''' Save filepaths for the feed and stats '''
        Log.debug("IO.stats", "Initializing")
        self._filepath = filepath
        self._save = save
        self._stats_dict = None

    @property
    def data(self):
        ''' Returns a dictionary of tweet stats from var or disk. '''
        if not self._stats_dict:
            try:
                Log.debug("IO.stats", "Loading stats from " + self._filepath)
                self._stats_dict = FileIO.get_json_dict(self._filepath)
            except FileNotFoundError:
                # Create default stats dictionary
                Log.debug("IO.stats", "Couldn't find stats file")
                self._stats_dict = {'feed_index': 0, 'id_to_title': {}, 'tweets': {}}
                assert self.last_feed_index == 0

        return self._stats_dict

    @property
    def last_feed_index(self) -> int:
        ''' The last saved feed index as saved in the stats file. '''
        return self.data['feed_index']

    @last_feed_index.setter
    def last_feed_index(self, value: int):
        ''' Save the most recent feed index '''
        if value < 0:
            raise IndexError
        self.data['feed_index'] = value
        self._write_stats_file()

    def find_title_from_id(self, twid):
        ''' Converts a Tweet ID, given by Twitter, into a hash title. '''
        if twid in self.data['id_to_title']:
            return self.data['id_to_title'][twid]
        else:
            return None

    def get_tweet_stats(self, title_or_id):
        ''' Returns a dictionary that details the performance of a tweet '''
        title = self.find_title_from_id(title_or_id) or title_or_id
        try:
            return self.data['tweets'][title]
        except KeyError:
            Log.warning("IO.get_stats", "No stats found for " + title)
            return None

    def mod_tweet_stats(self, title: str, stat_name: str, value):
        ''' Adds a value (int or list) to a given [stat_name] for Tweet [title]. '''
        t_stats = self.get_tweet_stats(title)
        if t_stats:
            t_stats[stat_name] += value
            self._write_stats_file()
        else:
            Log.info("IO.mod_stats", "Get failed. See above. ")

    def register_tweet(self, twid: int, title: str):
        ''' Save a newly published Tweet to the stats dictionary '''
        Log.debug("IO.stats", "Preparing to register tweet...")
        if not self.get_tweet_stats(title):
            blank_perf_stats = {
                'favorites': 0,
                'retweets': 0,
                'requotes': 0,
                'replies': 0,
                'rt_comments': []
            }
            Log.debug("IO.stats", "Registering tweet: " + title)
            self.data['id_to_title'][twid] = title
            self.data['tweets'][title] = blank_perf_stats
            self._write_stats_file()
        else:
            raise AlreadyRegisteredTweetError(title)

    def _write_stats_file(self):
        ''' Save the stats dict if it's dirty '''
        if self._save:
            Log.debug("IO.stats", "Saving stats file: " + self._filepath)
            FileIO.save_json_dict(self._filepath, self._stats_dict)

    def save_copy(self, ext):
        ''' Saves a copy of the current stats dictionary '''
        Log.debug("IO.stats", "Savin' a copy to "+self._filepath+"-"+ext)
        FileIO.save_json_dict(self._filepath+"-"+ext, self._stats_dict)

    def set_dirty(self):
        ''' Forces the stats object to reload the stats dictionary by first deleting it. '''
        self._stats_dict = None

