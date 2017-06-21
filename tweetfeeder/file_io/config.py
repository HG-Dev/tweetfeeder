''' Compile-time configuration data for hg_tweetfeeder.bot '''

from re import search
from datetime import datetime
from tweepy import OAuthHandler
from .utils import FileIO
from ..flags import BotFunctions
from ..exceptions import LoadConfigError

class Config:
    ''' Config data storage and processing for usage inside hg_tweetfeeder.bot '''
    def __init__(self, functionality, filepath: str = ""):
        self.tweet_time_strings = [] # Temp data holder
        self.keys = {} # Temp data holder
        self._filepaths = {} # Indirect access
        self.functionality = functionality
        self.authorization = None
        self.min_tweet_delay = 4
        self.bot_id = 0
        self.master_id = 0
        try: #Stage one, get serialized settings
            self.__dict__.update(FileIO.get_json_dict(filepath))
        except FileNotFoundError as e:
            raise LoadConfigError("Could not load settings JSON.") from e
        except ValueError as e: #Apparently JSONDecoderError inherits from this
            raise LoadConfigError("Settings JSON is faulty.") from e
        except AttributeError as e:
            raise LoadConfigError(
                "Settings JSON is incomplete."
            ) from e

        try:
            self.tweet_times = self.parse_tweet_times(self.tweet_time_strings)
        except ValueError as e:
            raise LoadConfigError(
                "Settings JSON has bad tweet times."
            ) from e
        except AttributeError as e:
            self.tweet_times = []

        try: #Stage two, get serialized credientials
            credentials = FileIO.get_json_dict(self._filepaths['auth'])
            self.__dict__.update(**credentials['twitter_ids']) #UPDATE IS HANDY!
            self.authorization = self.auth_from_keys(**credentials['keys'])
        except FileNotFoundError as e:
            raise LoadConfigError(
                "Settings JSON was loaded, " +
                "but its credentials filepath didn't work."
            ) from e
        except ValueError as e:
            raise LoadConfigError("Credentials JSON is faulty.") from e
        except (KeyError, AttributeError) as e:
            raise LoadConfigError("Credentials JSON is incomplete.") from e

    @property
    def feed_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self._filepaths['feed']

    @property
    def stats_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self._filepaths['stats']

    @property
    def log_filepath(self):
        ''' Return filepath to the log. '''
        return self._filepaths['log']

    @staticmethod
    def auth_from_keys(consumer_key, consumer_secret, access_token, access_token_secret):
        ''' Creates an authorization handler from credentials '''
        authorization = OAuthHandler(
            consumer_key, consumer_secret
        )
        authorization.set_access_token(
            access_token, access_token_secret
        )
        return authorization

    @staticmethod
    def parse_tweet_times(tt_list):
        ''' Converts easily read times into useful datetimes. '''
        tweet_times = []
        for itr, time_str in enumerate(tt_list):
            hour, minute = [int(x) for x in search(r'0?([12]?\d):0?([1-5]?\d)', time_str).groups()]
            try:
                tweet_times.append(
                    datetime.now().replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0
                    )
                )
            except ValueError as e:
                raise ValueError("Problem was with tweet_time #{}".format(itr+1)) from e
        return tweet_times
