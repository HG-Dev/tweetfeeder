"""
This module contains Exception classes specific to TweetFeeder
"""
from .logs import Log

class TweetFeederError(Exception):
    """
    Generalized base error class for TweetFeeder.
    Messages will be automatically saved to the event log,
    assuming logging functionality is enabled.
    """
    def __init__(self, err, msg):
        ''' Initializes the base Exception class. '''
        Log.error(err, msg)
        super(TweetFeederError, self).__init__(msg)

class LoadConfigError(TweetFeederError):
    ''' Raised when you fail to init a TweetFeederBot. '''
    def __init__(self, msg):
        super(LoadConfigError, self).__init__(type(self).__name__, msg)
