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
        if self._total_tweets == 0:
            try:
                self.get_tweets(0)
            except LoadFeedError:
                return 0
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
            try:
                while feed_data[index+itr]['chain']:
                    itr += 1 #Append next tweet
                    if index + itr >= self.total_tweets:
                        break # Don't allow a final 'chain' to cause an index error
                    next_tweets.append(feed_data[index + itr])
            except KeyError: #Tweet data lacked the chain element -> defaults to False
                pass

        return next_tweets

class Stats:
    ''' Access to Tweet stats and session data '''

    def __init__(self, filepath: str = None, save: bool = False):
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
                self._stats_dict = FileIO.get_json_dict(self._filepath)
            except (FileNotFoundError, TypeError):
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

    def find_title_from_id(self, twid: str):
        ''' Converts a Tweet ID, given by Twitter, into a hash title. '''
        if str(twid) in self.data['id_to_title'].keys():
            return self.data['id_to_title'][str(twid)]
        else:
            return None

    def get_tweet_stats(self, title_or_id):
        ''' Returns a dictionary that details the performance of a tweet '''
        title = self.find_title_from_id(str(title_or_id)) or title_or_id
        try:
            return self.data['tweets'][title]
        except KeyError:
            Log.debug("IO.get_stats", "No stats found for {}".format(title))
            return None

    def mod_tweet_stats(self, title_or_id, stat_name: str, value):
        ''' Adds a value (int or list) to a given [stat_name] for Tweet [title]. '''
        t_stats = self.get_tweet_stats(title_or_id)
        if t_stats:
            if isinstance(t_stats[stat_name], list):
                t_stats.append(value)
            else:
                t_stats[stat_name] += value
            self._write_stats_file()
        else:
            Log.debug("IO.mod_stats", "Get failed. See above. ")

    def update_tweet_stats(self, title_or_id, stats):
        ''' Updates dict elements that detail the performance of a tweet '''
        title = self.find_title_from_id(str(title_or_id)) or title_or_id
        Log.debug("IO.update_stats", "Updating stats for {}:\n{}".format(title, stats))
        try:
            self.data['tweets'][title].update(stats)
            self._write_stats_file()
        except KeyError:
            Log.warning("IO.update_stats", "No stats found for {}".format(title))

    def update_tweet_stats_from_status(self, tweet_object: dict):
        ''' Runs update_tweet_stats from a Tweepy status '''
        current_stats = {
            'favorites': tweet_object['favorite_count'],
            'retweets': tweet_object['retweet_count'],
        }
        self.update_tweet_stats(tweet_object['id'], current_stats)

    def register_tweet(self, twid: int, title: str = None):
        ''' Save a newly published Tweet to the stats dictionary '''
        Log.debug("IO.stats", "Saving tweet data...")
        if not self.get_tweet_stats(title):
            blank_perf_stats = {
                'favorites': 0,
                'retweets': 0,
                'requotes': 0,
                'replies': 0,
                'rt_comments': []
            }
            Log.debug("IO.stats", "Registering tweet: " + title)
            self.data['id_to_title'][str(twid)] = title
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

