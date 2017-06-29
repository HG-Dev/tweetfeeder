''' Main executable for the "hg_tweetfeeder" Twitter bot. '''

from tweetfeeder import TweetFeederBot
from tweetfeeder.flags import BotFunctions

def main():
    """ Main body for starting up and terminating Tweetfeeder bot """
    # pylint: disable=no-member
    try:

        bot = TweetFeederBot(BotFunctions.All, "config/settings.json")

    except KeyboardInterrupt:
        bot.shutdown() #TODO: Make this in master branch

if __name__ == "__main__":
    main()
