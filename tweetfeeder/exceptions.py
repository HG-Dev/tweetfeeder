"""
This module contains Exception classes specific to TweetFeeder
"""
from .logs import log

class TweetFeederError(Exception):
    """
    Generalized base error class for TweetFeeder.
    Messages will be automatically saved to the event log,
    assuming logging functionality is enabled.
    """
    def __init__(self, msg):
        ''' Initializes the base Exception class. '''
        log(self.__class__, msg)
        super(TweetFeederError, self).__init__(msg)

class LoadConfigError(TweetFeederError):
    ''' Raised when you fail to init a TweetFeederBot. '''
    pass
