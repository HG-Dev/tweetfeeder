''' Compile-time configuration data for hg_tweetfeeder.bot '''
from os import path, mkdir
from re import search, sub
from configparser import ConfigParser, ParsingError
from datetime import datetime
from tweepy import OAuthHandler
from .utils import FileIO
from ..flags import BotFunctions
from ..exceptions import LoadConfigError

class Config:
    ''' Regenerative .ini config file interpretation for usage inside hg_tweetfeeder.bot '''
    def __init__(self, functionality, on_change: classmethod, filepath: str = None):
        # Attempt to load config file from given filepath
        config = ConfigParser(allow_no_value=True)
        if filepath:
            file_ext = path.splitext(filepath)[-1]
            if not file_ext:
                filepath += ".ini" # TODO: Warning of missing extension?
            elif file_ext != ".ini":
                raise LoadConfigError("TweetFeeder config file should be of .ini type.")
            
            if path.exists(filepath):
                try:
                    assert path.isfile(filepath)
                    config.read(filepath)          
                except (AssertionError, ParsingError) as e:
                    raise LoadConfigError("Error parsing config ({}).".format(filepath))
            else:
                raise LoadConfigError("No config file at given filepath ({}).".format(filepath))
        
        # Internal dictionary that represents the config file's sections, options, and default values
        # All string values can be called safely from this dictionary (see properties)
        self._config_dict = {
            "Filepaths" : {
                'feed'  : None,
                'stats' : None,
                'log'   : None,
                'auth'  : None
            },
            "Tweet Settings" : {
                'tweet_times_list'  : "XX:XX, XX:XX",
                'rand_deviation'    : "0 minutes",
                'rest_period'       : "0 seconds",
                'min_tweet_delay'   : "4 seconds",
                'looping_min_score' : "0 points",
                'looping_max_times' : "0 times"
            }
        }

        self.bot_id = 0
        self.master_id = 0
        self.tweet_times = []
        # These four values will be updated in internal dictionary loop
        self.rand_deviation = 0
        self.rest_period = 0
        self.min_tweet_delay = 4
        self.looping_min_score = 0 # Score necessary to rerun a tweet
        self.looping_max_times = 0 # Number of times the feed can be looped over (disabled by default)

        # Iterate over internal dictionary to both update self.values and generate config file
        for section, option_dict in self._config_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            for option, value in option_dict.items():
                if not config.has_option(section, option):
                    config.set(section, option, value)
                else:
                    self._config_dict[section][option] = config.get(section, option)
                    if option in self.__dict__: #Update integer self.values
                        try:
                            self.__dict__[option] = int(sub("[^\d]", "", config.get(section, option)) or self.__dict__[option])
                        except ValueError:
                            raise LoadConfigError("Error parsing integer from option: {}={}".format(option, sub("[^\d]", "", config.get(section, option))))

        # Check filepaths before proceeding
        path_errors = self.verify_paths()
        if path_errors:
            raise LoadConfigError("The following paths failed verification: " + str(path_errors))

        self.authorization = None
        if self._config_dict["Filepaths"]['auth']:
            try: # Get serialized credientials
                credentials = FileIO.get_json_dict(self._config_dict["Filepaths"]['auth'])
                self.__dict__.update(**credentials['twitter_ids']) # Updates bot_id and master_id
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

        # Read tweet times and split the string
        self.tweet_times = []
        if "X" not in self._config_dict["Tweet Settings"]["tweet_times_list"]:
            tweet_time_strings = sub("[^\d:]", " ", self._config_dict["Tweet Settings"]["tweet_times_list"]).split()
            try:
                self.tweet_times = self.parse_tweet_times(tweet_time_strings)
            except ValueError as e:
                raise LoadConfigError(
                    "Settings JSON has bad tweet times."
                ) from e
        
        self.on_change = on_change or Config.on_change_dummy
        self._functionality = functionality

        # Save config file, adding missing options or sections
        if filepath:
            with open(filepath, 'w') as configfile:
                config.write(configfile)

    @property
    def feed_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self._config_dict["Filepaths"]['feed']

    @property
    def stats_filepath(self):
        ''' Returns filepath to the tweet feed. '''
        return self._config_dict["Filepaths"]['stats']

    @property
    def log_filepath(self):
        ''' Return filepath to the log. '''
        return self._config_dict["Filepaths"]['log']

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
            try:
                hour, minute = [int(x) for x in search(r'0?([12]?\d):0?([1-5]?\d)', time_str).groups()]
            except AttributeError:
                raise ValueError("Unable to parse tweet_time string: {}".format(time_str))
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
        for filepath in self._config_dict["Filepaths"].values():
            if filepath:
                # If the file has yet to be created, ensure it can be written to
                if not path.exists(path.dirname(filepath)):
                    try:
                        mkdir(filepath)
                    except OSError as e:                  
                        problems.add(path.dirname(filepath) + ": " + str(e))
        return problems
