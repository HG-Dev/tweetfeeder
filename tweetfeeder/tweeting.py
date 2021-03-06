"""
Timed Tweet publishing
"""
from threading import Timer, Event
from datetime import datetime, timedelta
from queue import deque
from time import sleep
from random import uniform
from tweepy import API
from tweepy.models import Status
from tweepy.error import TweepError
from tweetfeeder.logs import Log
from tweetfeeder.file_io.models import Feed, Stats
from tweetfeeder.exceptions import TweetFeederError, LoadFeedError, NoTimerError, ExistingTimerError
from tweetfeeder.file_io.config import Config

class TweetLoop():
    ''' Interprets TweetFeeder configuration to publish Tweets on a schedule '''
    def __init__(self, config: Config, feed: Feed, stats: Stats = None):
        """
        Creates an object capable of timed publishing of Tweets.
        Automatically starts if config.functionality.Tweet
        """
        self.config = config
        self.api = API(self.config.authorization, retry_count=1, retry_delay=10, wait_on_rate_limit=True)
        self.feed: Feed = feed
        self.stats: Stats = stats or Stats()
        self.current_index: int = 0 #Set in start
        self.current_timer: Timer = None
        self._current_started = datetime.now()
        self.lock: Event = Event()
        self.timers: deque = deque()
        if config.functionality.Tweet:
            self.start()


    def get_next_tweet_datetime(self):
        ''' Gets the next datetime at which tweeting will occur. '''
        # Supply immediate times if no tweet times
        if not self.config.tweet_times:
            Log.debug("TWT.datetime", "No tweet times; tweet NOW")
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

            Log.debug("TWT.datetime", "Compare now {} to next {}".format(now_t, next_t))
            if now_t > next_t: #The final time lies before the current
                next_t = next_t + timedelta(days=1)

            if self.config.rand_deviation: #Add random deviation in minutes
                next_t = next_t + timedelta(minutes=(self.config.rand_deviation * uniform(-1, 1)))    
                Log.debug("TWT.datatime", "Added random deviation to next {}".format(next_t))

            for time in self.config.tweet_times:
                next_t = next_t.replace(hour=time.hour, minute=time.minute)
                if now_t < next_t: # If next_t is in the future
                    return next_t.replace(second=0)
        #Failure
        return None


    def start(self):
        ''' Begin the tweet loop '''
        if not self.is_running():
            self.lock.set()
            self.current_index = self.stats.last_feed_index
            Log.debug("TWT.start", "Set current index to " + str(self.current_index))
            # Add the next timer tweet starting from
            # the last successfully tweeted index
            self._next()
            self.lock.clear()
        else:
            Log.warning("TWT.start", "Couldn't start: Loop is already running")

    def _next(self):
        ''' When only one timer is left, queue up more '''
        # Replenish timers when all queued timers have been popped off
        if not self.timers:
            Log.debug("TWT.next", "Creating next timers")

            # Check to see that the current_index hasn't reached the end of the feed
            if self.current_index >= self.feed.total_tweets:
                if self.stats.times_rerun < self.config.looping_max_times:
                    # If looping's enabled, loop the index around
                    Log.info("TWT.next", "Looping back to start of feed.")
                    self.stats.times_rerun = self.stats.times_rerun + 1
                    self.stats.last_rerun_index = self.current_index
                    self.current_index = 0
                else:
                    # Terminate loop
                    Log.info("TWT.next", "Reached end of feed, but not allowed to loop.")
                    self.stop()
                    return False
            
            # Check to see that the current_index has not surpassed a previous rerun
            if self.stats.last_rerun_index > 0 and self.current_index > self.stats.last_rerun_index:
                self.stats.times_rerun = 0 # Restore normal tweeting mode

            # make_tweet_timers will start searching from current_index,
            # but will continue iterating down the feed until it finds timers
            # it can actually use (this is important in rerun mode)
            index_inc = 0
            for timer in self._make_tweet_timers(self.current_index):
                #_make_tweet_timers passes back None for spots where reruns are not allowed
                index_inc += 1
                if timer:
                    # Skip None, but count it as a passed index
                    self.timers.append(timer)
                    Log.debug("TWT.next", "Timer: " + str(timer))
            if self.timers: # Set first timer to wait until next tweet time
                self.timers[0].interval = (
                    (self.get_next_tweet_datetime() - datetime.now()).total_seconds()
                )
                # If a rest_period is required, add it as a final Timer
                # This can be used to alternate between tweet times on different days
                # This does not affect index_inc
                if self.config.rest_period:
                    self.timers.append(
                        Timer(abs(self.config.rest_period), self._next)
                    )
            # Update current index with the feed entries both used and skipped
            self.current_index += index_inc

        if self.current_timer and not self.lock.is_set() and self.current_timer.args:
            # Current timer exists, but hasn't tweeted yet; fast forward
            self.current_timer.cancel()
            Log.debug("TWT.next", "Fast forward")
            self._tweet(*self.current_timer.args)
            # Update queued timer intervals
        elif self.timers:
            # current_timer is finishing up tweeting or doesn't exist;
            # pop off a timer and start it
            self.current_timer = self.timers.popleft()
            self.current_timer.start()
            self._current_started = datetime.now()
            Log.debug("TWT.next", "Starting new timer with interval {}".format(self.current_timer.interval))
        else:
            # No timers were created or the last timer was just a delay
            Log.debug("TWT.next", "Forced into recursion as no timers were produced")
            return self._next()
        return True

    def stop(self):
        ''' Cancels the current timer, which prevents futher timers from starting. '''
        Log.info("TWT.stop", "Stopping current timer and clearing timer list.")
        if self.current_timer:
            self.current_timer.cancel()
            self.timers.clear()

    def _make_tweet_timers(self, from_index: int):
        ''' Returns a tweet timer (multiple if chained), all with the same interval. '''
        # This can throw a LoadFeedError
        Log.debug("TWT.make_timers", "Making tweet timers starting from {}".format(from_index))
        try:
            next_tweets = self.feed.get_tweets(from_index)
        except LoadFeedError:
            return [None] #Returning one None will increase the current index, at least

        timers = []
        for idx, t_data in enumerate(next_tweets):
            # If rerunning, skip tweets which don't have a True "rerun" trait
            if self.stats.times_rerun > 0 and not t_data['rerun']:
                timers.append(None)
            else:
                timers.append(
                    Timer(self.config.min_tweet_delay, self._tweet, (t_data, from_index+idx))
                )
        return timers

    def _tweet(self, data: dict, index: int):
        ''' Tweet, then signal for the next to begin '''
        assert not self.lock.is_set()
        self.lock.set()
        success = 1
        if self.config.functionality.Online:
            Log.debug("TWT.tweet", "update_status using {}".format(data['title']))
            try:
                status = self.api.update_status(data['text'])
            except TweepError as e: #TODO: Switch over to Tweepy's retry system, configurable when creating API
                Log.error("TWT.tweet", str(e))
                success = 0
            else:
                Log.debug("TWT.tweet (id)", "Status ID: {}".format(status.id))
                self.stats.register_tweet(status.id, data['title'])
        else:
            Log.info("TWT.tweet", data['title'])
        self.stats.last_feed_index = index + success
        self._next()
        self.lock.clear()

    def wait_for_tweet(self, timeout=None, timer_expected=True, last_timer=False):
        ''' Hangs up the calling thread while the CURRENT timer loops. '''
        if self.current_timer and not self.current_timer.finished.is_set() and not last_timer:
            return self.current_timer.finished.wait(timeout)
        search = self.timers
        if last_timer:
            search = reversed(self.timers)
        for timer in search:
            if not timer.finished.is_set():
                Log.debug("TWT.wait", "Selected timer: " + str(timer))
                return timer.finished.wait(timeout)
        if timer_expected:
            raise NoTimerError("No tweet timers available to wait for")

    def time_until_tweet(self):
        ''' Returns the amount of time until the current timer finishes naturally. '''
        if self.is_running():
            return self.current_timer.interval - (datetime.now() - self._current_started).total_seconds()
        else:
            return -1

    def force_tweet(self):
        ''' Forces the oldest timer to finish immediately. '''
        self._next()

    def is_running(self):
        ''' Returns true if the TweetLoop has non-popped timers. '''
        if self.lock.is_set() or (self.current_timer and not self.current_timer.finished.is_set()):
            return True
        return False
