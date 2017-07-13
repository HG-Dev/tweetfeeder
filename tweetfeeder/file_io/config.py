''' Compile-time configuration data for hg_tweetfeeder.bot '''
from os import path, mkdir
from re import search
from datetime import datetime
from tweepy import OAuthHandler
from .utils import FileIO
from ..flags import BotFunctions
from ..exceptions import LoadConfigError

class Config:
    ''' Config data storage and processing for usage inside hg_tweetfeeder.bot '''
    def __init__(self, functionality, on_change: classmethod, filepath: str = None):
        self.tweet_time_strings = [] # Temp data holder
        self.keys = {} # Temp data holder
        self.filepaths = {'feed': None, 'stats': None, 'log': None, 'auth': None}
        self.on_change = on_change or Config.on_change_dummy
        self._functionality = functionality
        self.authorization = None
        self.min_tweet_delay = 4
        self.bot_id = 0
        self.master_id = 0
        if not filepath:
            return
        try: #Stage one, get serialized settings
            config_dict = FileIO.get_json_dict(filepath)
            self.__dict__.update(config_dict)
        except (ValueError) as e: #This isn't catching for some reason, but oh well
            raise LoadConfigError("Settings JSON is faulty: " + str(FileIO.get_json_dict(filepath))) from e
        except FileNotFoundError as e:
            raise LoadConfigError("Could not load settings JSON.") from e
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

        path_errors = self.verify_paths()
        if path_errors:
            raise LoadConfigError("The following paths failed verification: " + str(path_errors))

        try: #Stage two, get serialized credientials
            credentials = FileIO.get_json_dict(self.filepaths['auth'])
            self.__dict__.update(**credentials['twitter_ids']) #UPDATE IS HANDY!
            self.authorization = self.auth_from_keys(**credentials['keys'])
        except FileNotFoundError as e:
            raise LoadConfigError(
                "Settings JSON was loaded, " +
                "but its credentials filepath didn't work."
            ) from e
        except (ValueError, TypeError) as e:
            raise LoadConfigError("Credentials JSON is faulty.") from e
        except (KeyError, AttributeError) as e:
            raise LoadConfigError("Credentials JSON is incomplete.") from e

    @property
    def feed_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self.filepaths['feed']

    @property
    def stats_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self.filepaths['stats']

    @property
    def log_filepath(self):
        ''' Return filepath to the log. '''
        return self.filepaths['log']

    @property
    def functionality(self) -> BotFunctions:
        ''' Returns BotFunctions settings '''
        return self._functionality

    @functionality.setter
    def functionality(self, value: BotFunctions):
        ''' Modifies BotFunctions, then alerts a parent using on_change(). '''
        self._functionality = value
        self.on_change()

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

    @staticmethod
    def on_change_dummy():
        ''' Do nothing on change '''
        pass

    def verify_paths(self):
        ''' Ensures that the paths given for feed/stats files can be used. '''
        problems = set()
        for filepath in self.filepaths.values():
            if filepath:
                if not path.exists(path.dirname(filepath)):
                    try:
                        mkdir(filepath)
                    except OSError as e:                  
                        problems.add(path.dirname(filepath) + ": " + str(e))
        return problems
