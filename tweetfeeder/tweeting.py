"""
Timed Tweet publishing
"""
from threading import Timer
from datetime import datetime, timedelta
from time import sleep
from tweepy import API
from tweepy.models import Status
from tweetfeeder.logs import Log
from tweetfeeder.file_io.models import Feed
from tweetfeeder.exceptions import LoadFeedError, NoTimerError
from tweetfeeder.file_io.config import Config

class TweetLoop():
    ''' Interprets TweetFeeder configuration to publish Tweets on a schedule '''
    def __init__(self, config: Config, api: API, auto_start=True):
        ''' Creates an object capable of timed publishing of Tweets '''
        self.config = config
        self.api = api
        self.feed = Feed(config)
        self.current_wait = 60
        #self.publish_method = None
        self._timer: Timer = None
        if auto_start:
            self.start()


    def get_next_tweet_datetime(self):
        ''' Gets the next datetime at which tweeting will occur. '''
        # Supply immediate times if no tweet times and tweeting offline
        if not self.config.tweet_times and not self.config.functionality.Online:
            return (
                datetime.now() +
                timedelta(seconds=self.config.min_tweet_delay*0.2)
            )
        # Offline or not, if there are tweet times, use them
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
                Log.debug("tweeting.get_next_dt", "Compare: next {} to {}".format(next_t, now_t))
                if now_t < next_t: # If next_t is in the future
                    Log.debug("tweeting.get_next_dt", "Returning " + str(next_t.replace(second=0)))
                    return next_t.replace(second=0)
        #Failure
        return None

    def start(self):
        ''' Begin the tweet loop '''
        self._timer = self._make_tweet_timer(self.feed.current_index)
        self._timer.start()
        return self._timer

    def stop(self):
        ''' Cancels the tweeting loop. '''
        try:
            self._timer.cancel()
        except AttributeError:
            raise NoTimerError("Unable to cancel timer.")

    def _make_tweet_timer(self, from_index: int):
        ''' Loads and schedules tweet(s) '''
        # This can throw a LoadFeedError
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
        Log.info("tweeting.tweet", log_str)
        if self.config.functionality.Online:
            for tweet in tweets:
                status = self.api.update_status(tweet['text'])
                Log.debug("", str(status))
                sleep(self.config.min_tweet_delay)
        next_index = from_index + len(tweets)
        self.feed.set_last_index(next_index)
        try:
            self.start() # Start again
        except LoadFeedError:
            pass

    def wait_for_tweet(self, timeout=None):
        ''' Hangs up the calling thread while the CURRENT timer loops. '''
        try:
            return self._timer.finished.wait(timeout)
        except AttributeError:
            raise NoTimerError("Cannot wait for a nonexistant timer.")

    def is_running(self):
        ''' Returns true if the TweetLoop has an active timer. '''
        if self._timer is None:
            return False
        else:
            return not self._timer.finished.is_set()
