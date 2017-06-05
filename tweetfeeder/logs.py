''' Logging for events in TweetFeeder '''
import logging

TF_LOGGER = logging.getLogger('TweetFeeder')

def log(ev_type, msg):
    ''' Wrapper for the logging module's log methods. '''
    ev_type_txt = str(ev_type).split('.')[-1].replace("'>", "")
    text = "{:<18}: {}".format(ev_type_txt, msg)
    #TODO: Implement bot events to accompany exceptions
    TF_LOGGER.info(text)
    print(text) #Temporary
