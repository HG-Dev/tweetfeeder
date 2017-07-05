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
from tweetfeeder.exceptions import LoadFeedError, NoTimerError
from tweetfeeder.file_io.config import Config
# NOTE: the Stats() is preserved, so it must be marked dirty upon "initializing"
class TweetLoop():
    ''' Interprets TweetFeeder configuration to publish Tweets on a schedule '''
    def __init__(self, config: Config, feed: Feed, stats: Stats = Stats()):
        """
        Creates an object capable of timed publishing of Tweets.
        Automatically starts if config.functionality.Tweet
        """
        self.config = config
        self.api = API(self.config.authorization)
        self.feed: Feed = feed
        self.stats: Stats = stats
        self.stats.set_dirty() # Fixes problem with cached "new" Stats()
        self.current_wait = 60
        #self.publish_method = None
        self._timers = deque(maxlen=3)
        self._halt_flag = Event()
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
                Log.debug("TWT.get_next_dt", "Compare: next {} to {}".format(next_t, now_t))
                if now_t < next_t: # If next_t is in the future
                    Log.debug("TWT.get_next_dt", "Returning " + str(next_t.replace(second=0)))
                    return next_t.replace(second=0)
        #Failure
        return None

    def start(self):
        ''' Begin the tweet loop '''
        if not self.config.functionality.Tweet:
            Log.warning("TWT.start", "Prevent inconsistency by enabling BotFunctions.Tweet")
        timer = self._make_tweet_timer(self.stats.last_feed_index)
        Log.debug("TWT.start", "Starting timer #" + str(id(timer)))
        timer.start()
        self._timers.append(timer)
        Log.debug("TWT.start", "Added to timers: {}".format(len(self._timers)))
        return timer

    def stop(self):
        ''' Cancels the tweeting loop, causing it to stop. '''
        self._halt_flag.set()
        try:
            for timer in self._timers:
                Log.debug("TWT.stop", "Stopping timer #" + str(id(timer)))
                timer.cancel()
            self._timers.clear()
        except AttributeError:
            pass # Probably never started to begin with

    def _make_tweet_timer(self, from_index: int):
        ''' Loads and schedules tweet(s) '''
        # This can throw a LoadFeedError
        Log.debug("TWT.make_timer", "Gettings tweets from " + str(from_index))
        next_tweets = self.feed.get_tweets(from_index)

        delta = self.get_next_tweet_datetime() - datetime.now()
        self.current_wait = delta.total_seconds()
        return Timer(
            self.current_wait,
            self._tweet,
            (next_tweets, from_index)
        )

    def _tweet(self, tweets: list, from_index: int):
        ''' Tweet, then signal for the next to begin '''
        log_str = "{} tweet{} starting at {} ({})".format(
            len(tweets),
            's' if (len(tweets) > 1) else '',
            from_index+1, # Index from 1
            tweets[0]['title']
            )
        Log.info("TWT.tweet", log_str)
        for itr, tweet in enumerate(tweets):
            if self.config.functionality.Online:
                status = self.api.update_status(tweet['text'])
                Log.debug("TWT.tweet (id)", str(status.id))
                self.stats.register_tweet(status.id, tweet['title'])
            self.stats.last_feed_index = from_index + itr + 1
            sleep(self.config.min_tweet_delay)

        if not self._halt_flag.is_set():
            try:
                if self._timers:
                    self._timers.pop()
                self.start() # Start again
            except LoadFeedError:
                pass
        else: # Skip the next timer step
            self._halt_flag.clear()

    def wait_for_tweet(self, timeout=None):
        ''' Hangs up the calling thread while the CURRENT timer loops. '''
        try:
            return self._timers[-1].finished.wait(timeout)
        except (AttributeError, IndexError):
            raise NoTimerError("Cannot find timer to wait for.")

    def is_running(self):
        ''' Returns true if the TweetLoop has an active timer. '''
        for timer in self._timers:
            if not timer.finished.is_set():
                return True
        return False
