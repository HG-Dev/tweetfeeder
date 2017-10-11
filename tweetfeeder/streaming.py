"""
UserStream listener for use by TweetFeederBot.
"""
import json
from threading import Timer
from tweepy import StreamListener, API
from tweetfeeder.logs import Log
from tweetfeeder.file_io import Config
from tweetfeeder.file_io.models import Feed, Stats
from tweetfeeder.file_io.utils import FileIO
from tweetfeeder.exceptions import InvalidCommand, UnregisteredTweetError, ArgumentError

class TweetFeederListener(StreamListener):
    """
    Receives events from Tweepy
    """
    def __init__(self, config: Config, stats: Stats, cmd_method: classmethod):
        """
        Creates a TweetFeederListener using config data
        and Tweepy API from a TweetFeederBot.
        """
        self._config = config
        self._stats = stats
        self.cmd_method = cmd_method
        self.api = API(config.authorization)
        self.timers = []
        self.check_delay = 420  #Seven minutes
        super(TweetFeederListener, self).__init__(self.api)

    def on_connect(self):
        '''Called once connected to streaming server.'''
        Log.debug("STR.on_connect", "Now listening for userstream events.")

    def on_data(self, raw_data):
        '''Debug wrapper for StreamListener.on_data'''
        if raw_data is None:
            Log.debug("STR.on_data", "Received empty streaming data")
        elif super(TweetFeederListener, self).on_data(raw_data) is False:
            Log.error("STR.on_data", "Streaming halt!")

    def on_direct_message(self, status):
        ''' Called when a new direct message arrives '''
        sender_id = status.direct_message['sender_id']
        # Message from user arrives
        if sender_id != self._config.bot_id:
            # Log message
            Log.debug("STR.on_dm", "{}: {}".format(
                status.direct_message['sender_screen_name'],
                status.direct_message['text']
            ))
            if sender_id == self._config.master_id:
                # Message from master arrives
                try:
                    self.cmd_method(status.direct_message['text'])
                except InvalidCommand:
                    pass #The exception will be automatically logged
            else:
                # Interact with other users?
                # Perhaps a project for another day.
                pass

    def on_event(self, status):
        """
        Called when a new event arrives.
        This responds to "favorite" and "quoted_tweet."
        """
        absolute = ['favorite', 'unfavorite']
        relative_pos = ['quoted_tweet']
        ignored = ['follow']
        actor = status.source['screen_name']
        info = ""

        if status.event in absolute: # these have a target_object
            self._stats.update_tweet_stats_from_status(status.target_object)
            info = status.target_object['id']
        elif status.event in relative_pos:
            self._stats.mod_tweet_stats(status.target_object['id'], 'requotes', 1)
        elif status.event in ignored:
            return True #False would stop streaming
        else:
            Log.warning("STR.on_event", "Unhandled event: " + status.event)
            return True
        Log.info("STR.on_event", "{} {}: {}".format(status.event, actor, info))

    def on_status(self, status):
        ''' Called when a new status arrives. '''
        event = ""
        actor = ""
        info = ""
        if hasattr(status, 'retweeted_status') and status.retweeted_status.user.id == self._config.bot_id:
            event = "retweet"
            actor = status.user.screen_name
            info = status.retweeted_status.id
            self._stats.update_tweet_stats_from_status(status.retweeted_status.__dict__) #Retweeted status isn't a dict
            timer = Timer(self.check_delay, self.check_for_comments, (info, status.user.id))
            timer.start()
            self.timers.append(timer)
        elif status.in_reply_to_user_id == self._config.bot_id:
            event = "reply"
            actor = status.author.screen_name
            info = status.text
            tweet_id = status.in_reply_to_status_id
            self._stats.mod_tweet_stats(tweet_id, "replies", 1)
        elif status.author.id == self._config.bot_id:
            if not status.in_reply_to_user_id:
                event = "tweet"
                actor = "confirmed"
                info = status.id
                #Non-reply should already be registered... unless it was tweeted directly.
                if not self._stats.find_title_from_id(info):
                    Log.warning("STR.on_status", "Add to feed? <{}>".format(status.text))
                    return True
            else:
                return True #Ignore manual or possibly automatic interactions with users
        elif status.is_quote_status:
            return True #Ignore; this will be picked up by on_event
        elif not status.in_reply_to_user_id:
            return True #Ignore; this is just a mention or master tweet
        elif status.author.id != self._config.master_id:
            # Oddball catch-all
            Log.warning(
                "STR.on_status",
                "on_status?: " + status.id_str
            )
            return True
        Log.info(
            "STR.on_status",
            "{} {}: {}".format(
                event,
                actor,
                info
                )
        )
        return True

    def on_disconnect(self, notice):
        ''' Called, presumably, when Twitter disconnects us for an error. '''
        self.cancel_checks()
        Log.warning("STR.on_disconnect", "Streaming: " + notice)

    def check_for_comments(self, tweet_id, user_id=None, user_timeline=None):
        ''' Checks a list of statuses (downloads them if necessary) for any comments made after a retweet '''
        Log.debug("STR.rt_check", "Checking for comments on retweet...")
        if not user_id and not user_timeline:
            raise ArgumentError("check_for_comments requires user_id or user_timeline")

        if not user_timeline:
            user_timeline = self.api.user_timeline(id=user_id)

        twenty_statuses = reversed(user_timeline)
        pick_up_next = False
        potential_comment = None
        for status in twenty_statuses:
            if pick_up_next:
                potential_comment = status
                break
            try:
                if status.retweeted_status.id == tweet_id:
                    pick_up_next = True
            except AttributeError:
                pass
        if potential_comment:
            if 'RT' in potential_comment.text and not 'RT @' in potential_comment.text:
                Log.info("STR.rt_check", "User ({}) commented on retweet!".format(potential_comment.user.screen_name))
                # Add related text to rt_comments
                self._stats.mod_tweet_stats(tweet_id, 'rt_comments', potential_comment.text)

        self._clear_finished_checks()

    def cancel_checks(self):
        ''' Cancel all timed checks of RT comments '''
        print("Cancelling timers: " + str(len(self.timers)))
        for timer in self.timers:
            timer.cancel()
        self.timers.clear()

    def _clear_finished_checks(self):
        ''' Clear list of all finished checks '''
        for timer in self.timers:
            if timer.finished.is_set() is True:
                self.timers.remove(timer)
