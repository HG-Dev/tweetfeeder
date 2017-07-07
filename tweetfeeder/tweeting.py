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
        self.stats.set_dirty() # Fixes problem with cached "new" Stats()
        self.current_wait = 60
        self.next_index = stats.last_feed_index
        self._timers = deque(maxlen=12)
        self._halt_flag = Event()
        self._spawn_finished = Event()
        self._spawn_finished.set()
        if config.functionality.Tweet:
            print("Beginning tweet loop")
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
        if not self.config.functionality.Tweet:
            raise TweetFeederError("TWT.start", "Prevent inconsistency by enabling BotFunctions.Tweet")
        if self.is_running():
            raise ExistingTimerError("Try using Shutdown first.")
        # Clear any previous halt command
        self._halt_flag.clear()
        # Start the first three timers
        self._next()

    def _next(self):
        ''' Create next timer, if necessary '''
        if self._halt_flag.is_set() or len(self._timers) > 10:
            # Timers exist, or no more timers are desired
            return None
        try:
            timers = self._make_tweet_timers(self.next_index)
            if timers:
                Log.info(
                    "TWT.next", "Adding timers for tweets #{}"
                    .format(range(self.next_index, self.next_index-1+len(timers)))
                )
                for timer in timers:
                    self._timers.appendleft(timer)
                    self.next_index += 1
                    timer.start()
            self._spawn_finished.set()
        except LoadFeedError:
            Log.error("TWT.next", "Reached end of Tweet feed!")
            return None

    def stop(self):
        ''' Cancels the tweeting loop, causing it to stop. '''
        self._halt_flag.set()
        self._spawn_finished.wait(10)
        try:
            for timer in self._timers:
                Log.debug("TWT.stop", "Stopping timer #" + str(id(timer)))
                timer.cancel()
            self._timers.clear()
        except AttributeError:
            pass # Probably never started to begin with

    def _make_tweet_timers(self, from_index: int):
        ''' Loads and schedules tweet(s) '''
        if self._halt_flag.is_set(): #TODO: Figure out how to make this actually thread safe
            return None
        Log.debug("TWT.make_timer", "Gettings tweets from " + str(from_index))
        # This can throw a LoadFeedError
        next_tweets = self.feed.get_tweets(from_index)
        ###
        timers = []
        delta = self.get_next_tweet_datetime() - datetime.now()
        self.current_wait = delta.total_seconds()

        for idx, tweet in enumerate(next_tweets):
            timers.append(
                Timer(
                    self.current_wait + self.config.min_tweet_delay * idx,
                    self._tweet,
                    (tweet, from_index+idx)
                )
            )

        return timers

    def _tweet(self, data: dict, index: int):
        ''' Tweet, then signal for the next to begin '''
        self._spawn_finished.clear()
        Log.info("TWT._tweet", "Tweeting " + data['title'])
        if self.config.functionality.Online:
            status = self.api.update_status(data['text'])
            Log.debug("TWT.tweet (id)", str(status.id))
            self.stats.register_tweet(status.id, data['title'])
        self.stats.last_feed_index = index + 1
        self._next() # Start next timer (unless timers remain or halt is set)
        if self._timers:
            self._timers.pop()

    def wait_for_tweet(self, timeout=None, timer_expected=True):
        ''' Hangs up the calling thread while the CURRENT timer loops. '''

        try:
            for timer in reversed(self._timers):
                # Get oldest timer
                if not timer.finished.is_set():
                    return timer.finished.wait(timeout)
            return self._spawn_finished.wait(timeout)
        except (AttributeError, IndexError):
            if timer_expected:
                raise NoTimerError("Cannot find timer to wait for.")

    def force_tweet(self):
        ''' Forces the oldest timer to finish immediately. '''
        self._spawn_finished.wait(10)
        if not self.is_running():
            Log.warning("TWT.force_tweet", "Loop not running")
        elif self._timers:
            Log.debug("TWT.force_tweet", "Forcing tweet: " + str(self._timers[-1].args[0]))
            args = self._timers[-1].args
            self._timers[-1].cancel()
            self._timers.pop()
            quick_timer = Timer(0, self._tweet, args)
            quick_timer.start()

    def is_running(self):
        ''' Returns true if the TweetLoop has non-popped timers. '''
        Log.info("TWT.running?timers:", self._timers)
        return self._timers or not self._spawn_finished.is_set()
