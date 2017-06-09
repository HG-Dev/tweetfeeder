"""
UserStream listener for use by TweetFeederBot.
"""
from tweepy import StreamListener
from tweetfeeder.logs import Log

class TweetFeederListener(StreamListener):
    """
    Receives events from Tweepy
    """
    def __init__(self, config, api):
        """
        Creates a TweetFeederListener using config data
        and Tweepy API from a TweetFeederBot.
        """
        self.config = config
        super(TweetFeederListener, self).__init__(api)

    def on_connect(self):
        '''Called once connected to streaming server.'''
        Log.info("STR.on_connect", "Now listening for userstream events.")

    def on_direct_message(self, status):
        ''' Called when a new direct message arrives '''
        sender_id = status.direct_message['sender_id']
        # Message from user arrives
        if sender_id != self.config.bot_id:
            # Log message
            Log.info("STR.on_dm", "{}: {}".format(
                status.direct_message['sender_screen_name'],
                status.direct_message['text']
            ))
            if sender_id == self.config.master_id:
                # Message from master arrives
                # TODO: Parse for command
                pass
            else:
                # Interact with other users?
                # Perhaps a project for another day.
                pass

    def on_event(self, status):
        """
        Called when a new event arrives.
        This responds to "favorite" and "quoted_tweet."
        """
        ignored = ['unfavorite', 'follow']
        actor = ""
        info = ""
        if status.event == "favorite": #This tends to come in delayed bunches
            actor = status.source['screen_name']
            info = status.target_object['id']
        elif status.event == "quoted_tweet":
            actor = status.source['screen_name']
            info = status.target_object['text']
        elif status.event in ignored:
            return False #no need to worry about accidental favoriting
        else:
            Log.warning("STR.on_event", "Unhandled event: " + status.event)
            return False
        Log.info("STR.on_event", "{} {}: {}".format(status.event, actor, info))

    def on_status(self, status):
        ''' Called when a new status arrives. '''
        event = ""
        actor = ""
        info = ""
        if hasattr(status, 'retweeted_status'):
            event = "retweet"
            actor = status.user.screen_name
            info = status.retweeted_status.id
        elif status.in_reply_to_user_id == self.config.bot_id:
            event = "reply"
            actor = status.author.screen_name
            info = status.text
        elif status.author.id == self.config.bot_id:
            if not status.in_reply_to_user_id:
                event = "tweet"
                actor = "confirmed"
                info = status.id
                #TODO: Register tweet in feed_tracking.json
            else:
                return False #Ignore manual or possibly automatic interactions with users
        elif status.is_quote_status:
            return False #Ignore; this will be picked up by on_event
        elif not status.in_reply_to_user_id:
            return False #Ignore; this is just a mention or master tweet
        else:
            Log.warning(
                "STR.on_status",
                "on_status?: " + status.id_str
            )
            return False
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
        Log.warning("STR.on_disconnect", "Streaming: " + notice)