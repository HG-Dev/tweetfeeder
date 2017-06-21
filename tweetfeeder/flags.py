''' Classifications for bot functionality '''

from flags import Flags

class BotFunctions(Flags):
    ''' Determines the functionality of a bot while running '''
    #Basic offline functionality
    Log = 1             # Log to file
    Listen = 2          # Watch UserStream
    Tweet = 4           # Publish tweets from feed at config's tweet times (if given)
    Online = 6          # If Listen and Tweet, Tweet over Twitter's API
    SaveStats = 8       # Save the last tweet index if TweetFromFeed, save tweet stats if Listen
    All = 15
