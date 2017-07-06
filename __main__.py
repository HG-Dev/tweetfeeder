''' Main executable for the "hg_tweetfeeder" Twitter bot. '''

from tweetfeeder import TweetFeederBot
from tweetfeeder.flags import BotFunctions

def main():
    """ Main body for starting up and terminating Tweetfeeder bot """
    # pylint: disable=no-member
    try:
        bot = TweetFeederBot(BotFunctions.All, "config/settings.json")
        bot.master_cmd.cmdloop()
    except KeyboardInterrupt:
        bot.shutdown()

if __name__ == "__main__":
    main()
