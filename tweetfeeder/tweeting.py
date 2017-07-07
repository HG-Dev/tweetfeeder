"""
Timed Tweet publishing
"""
from threading import Timer, Event
from datetime import datetime, timedelta
from queue import deque
from time import sleep
from tweepy import API
from tweepy.models import Status
from tweetfeeder.logs import Log
from tweetfeeder.file_io.models import Feed, Stats
from tweetfeeder.exceptions import TweetFeederError, LoadFeedError, NoTimerError, ExistingTimerError
from tweetfeeder.file_io.config import Config
# NOTE: the Stats() is preserved, so it must be marked dirty upon "initializing"
class TweetLoop():
    ''' Interprets TweetFeeder configuration to publish Tweets on a schedule '''
    def __init__(self, config: Config, feed: Feed, stats: Stats = None):
        """
        Creates an object capable of timed publishing of Tweets.
        Automatically starts if config.functionality.Tweet
        """
        self.config = config
        self.api = API(self.config.authorization)
        self.feed: Feed = feed
        self.stats: Stats = stats or Stats()
        self.current_timer_started: datetime = datetime.now()
        self.current_timer: Timer = None
        self.timers: deque = deque()
        if config.functionality.Tweet:
            self.start()


    def get_next_tweet_datetime(self):
        ''' Gets the next datetime at which tweeting will occur. '''
        # Supply immediate times if no tweet times
        if not self.config.tweet_times:
            return (
                datetime.now() +
                timedelta(seconds=self.config.min_tweet_delay*0.2)
            )

        if self.config.tweet_times:
            final_time = self.config.tweet_times[-1]
            now_t = datetime.now()
            next_t = now_t.replace(
                hour=final_time.hour,
                minute=final_time.minute,
                second=0,
                microsecond=0)

            if now_t > next_t: #The final time lies before the current
                next_t = next_t + timedelta(days=1)

            for time in self.config.tweet_times:
                next_t = next_t.replace(hour=time.hour, minute=time.minute)
                if now_t < next_t: # If next_t is in the future
                    return next_t.replace(second=0)
        #Failure
        return None


    def start(self):
        ''' Begin the tweet loop '''
        # Acquire the last successfully tweeted index
        self.timers.append(
            self._make_tweet_timers(datetime.now(), self.stats.last_feed_index)
        )
        self._next()

    def _next(self):
        ''' When only one timer is left, queue up more '''
        if self.current_timer and not self.current_timer.finished.is_set():
            # Fast foward
            self.current_timer.cancel()
            self._tweet(*self.current_timer.args)
        elif self.timers:
            self.current_timer = self.timers.popleft()
            self.current_timer.start()
            self.current_timer_started = datetime.now()
        # Replenish timers
        if self.current_timer and not self.timers:
            # Ran out of future timers

            # Set the timers to have intervals happening after the current timer finishes
            # TODO: Fix tweet skipping so that it resumes schedule
            self.timers.append(
                self._make_tweet_timers(from_time, self.stats.last_feed_index)
            )


    def stop(self):
        ''' Cancels the tweeting loop, causing it to stop. '''
        if self.current_timer:
            self.current_timer.cancel()
        for timer in self.timers:
            timer.cancel()

    def _make_tweet_timers(self, from_time: datetime, from_index: int):
        ''' Schedules a tweet '''
        # This can throw a LoadFeedError
        try:
            next_tweets = self.feed.get_tweets(from_index)
        except LoadFeedError:
            return None
        timers = []
        seconds = (self.get_next_tweet_datetime() - from_time).total_seconds()
        for idx, t_data in enumerate(next_tweets):
            timers.append(Timer(seconds, self._tweet, (t_data, from_index+idx)))
            seconds = self.config.min_tweet_delay

        return timers

    def _tweet(self, data: dict, index: int):
        ''' Tweet, then signal for the next to begin '''
        self._next()

    def wait_for_tweet(self, timeout=None, timer_expected=True):
        ''' Hangs up the calling thread while the CURRENT timer loops. '''

    def force_tweet(self):
        ''' Forces the oldest timer to finish immediately. '''

    def is_running(self):
        ''' Returns true if the TweetLoop has non-popped timers. '''
