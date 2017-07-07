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

class LoadFeedError(TweetFeederError):
    ''' Raised when you fail to load from the tweet feed. '''
    def __init__(self, msg):
        super(LoadFeedError, self).__init__(type(self).__name__, msg)

class NoTimerError(TweetFeederError):
    """
    Raised when an operation that requires a Tweet timer
    fails because the TweetLoop has no timer.
    """
    def __init__(self, msg):
        super(NoTimerError, self).__init__(type(self).__name__, msg)

class ExistingTimerError(TweetFeederError):
    """
    Raised when an attempt is made to start a TweetLoop,
    but a timer is already running.
    """
    def __init__(self, msg):
        super(ExistingTimerError, self).__init__(type(self).__name__, msg)

class UnregisteredTweetError(TweetFeederError):
    ''' Raised attempt to fetch data on a tweet not in stats. '''
    def __init__(self, msg):
        super(UnregisteredTweetError, self).__init__(type(self).__name__, msg)

class AlreadyRegisteredTweetError(TweetFeederError):
    ''' Raised when you attempt to save a "new" tweet when it's already registered. '''
    def __init__(self, msg):
        super(AlreadyRegisteredTweetError, self).__init__(type(self).__name__, msg)

class InvalidCommand(TweetFeederError):
    """
    Raised when command text, presumably from the master account,
    fails interpretation.
    """
    def __init__(self, msg):
        super(InvalidCommand, self).__init__(type(self).__name__, msg)
