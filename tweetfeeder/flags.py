''' Classifications for bot functionality '''

from flags import Flags

class BotFunctions(Flags):
    ''' Determines the functionality of a bot while running '''
    #Basic offline functionality
    LogToConsole = 1
    LogToFile = 2
    Log = 3 # Shorthand for both ToFile and ToConsole
