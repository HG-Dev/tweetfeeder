''' Compile-time configuration data for hg_tweetfeeder.bot '''

from re import search
from tweepy import OAuthHandler
from .utils import LoadFromFile
from ..exceptions import LoadConfigError

class Config:
    ''' Config data storage and processing for usage inside hg_tweetfeeder.bot '''
    def __init__(self, filepath=""):
        self.tweet_time_strings = [] # Temp data holder
        self.keys = {} # Temp data holder
        self.min_tweet_delay = 10
        self.filenames = {}
        self.authorization = None
        self.bot_id = 0
        self.master_id = 0
        try: #Stage one, get serialized settings
            self.__dict__ = LoadFromFile.get_json_dict(filepath)
            self.tweet_times = self.parse_tweet_times(self.tweet_time_strings)
        except FileNotFoundError:
            raise LoadConfigError("Could not load settings JSON.")
        except ValueError: #Apparently JSONDecoderError inherits from this
            raise LoadConfigError("Settings JSON is faulty.")
        except Exception as other_error:
            raise LoadConfigError(
                "Settings JSON is incomplete:\n" +
                str(other_error)
            )

        try: #Stage two, get serialized credientials
            credentials = LoadFromFile.get_json_dict(self.filenames['auth'])
            self.__dict__.update(**credentials['twitter_ids']) #THIS IS HANDY!
            self.authorization = self.auth_from_keys(**credentials['keys'])
        except FileNotFoundError:
            raise LoadConfigError(
                "Settings JSON was loaded," +
                " but its credentials filepath didn't work."
            )
        except ValueError:
            raise LoadConfigError("Credentials JSON is faulty.")
        except Exception as other_error:
            raise LoadConfigError(
                "Credentials JSON is incomplete:\n" +
                str(other_error)
            )

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
        ''' Converts easily read times into useful ints. '''
        tweet_times = []
        for time_str in tt_list:
            tweet_times.append(
                [int(x) for x in search(r'0?([12]?\d):0?([1-5]?\d)', time_str).groups()]
            )
        return tweet_times
