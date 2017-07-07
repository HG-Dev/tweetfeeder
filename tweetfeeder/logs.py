''' General logging wrapper for modules '''
import logging
from datetime import datetime, timedelta
from time import time

class Log:
    ''' Wrapper for LOGGER '''

    class DebugStream:
        ''' Pseudo stream for gathering log output '''
        def __init__(self):
            ''' Init buffer '''
            self.buffer = []

        def has_all_text(self, text_list=None):
            ''' Determine if a collection of text is in the log buffer '''
            if not text_list:
                return self.has_text()
            return all([self.has_text(x) for x in text_list])

        def has_text(self, text=None):
            ''' Determine if some text is in the log buffer '''
            if not text and self.buffer:
                return True #There's SOME record in here
            for record in self.buffer:
                if text in record:
                    return True
            return False

        def write(self, record):
            ''' Adds a log entry, ignoring unnecessary terminators '''
            if len(record) > 1:
                self.buffer.append(record)

        def clear(self):
            ''' Clears buffer '''
            self.buffer.clear()

    _handlers = {}
    _logger = logging.getLogger('Untitled: Use setup()')

    @staticmethod
    def setup(name, level=logging.INFO):
        ''' Initial setup; does logging.getLogger '''
        Log._logger = logging.getLogger(name)
        if Log._logger.level == logging.NOTSET:
            Log._logger.setLevel(level)

    @staticmethod
    def enable_console_output(enabled=True):
        ''' Adds or removes a stderr stream handler with logger '''
        console_handler = Log._enable_handler('console_output', enabled)
        if not console_handler and enabled:
            console_handler = logging.StreamHandler() #Defaults to sys.stderr
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s %(message)s', '%m/%d %H:%M')
            )
            console_handler.setLevel(logging.DEBUG)
            Log._enable_handler('console_output', enabled, console_handler)

    @staticmethod
    def enable_file_output(enabled=True, filepath=""):
        ''' Adds or removes a file output handler with logger '''
        # First create a new file handler to force an update
        if enabled:
            file_handler = logging.FileHandler(filepath, encoding='utf8')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s %(levelname)-7s %(message)s', '%m/%d/%y %H:%M:%S')
            )
            file_handler.setLevel(logging.INFO)
            Log._enable_handler('file_output', enabled, file_handler)
        else: # Just disable it
            Log._enable_handler('file_output', enabled)

    @staticmethod
    def enable_dm_output(enabled=True, send_method=None):
        ''' Creates a stream handler to the master Twitter account's DM inbox. '''
        if enabled and send_method:
            stream_handler = logging.StreamHandler(LogSender(send_method))
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(
                logging.Formatter('%(levelname)-7s %(message)s')
            )
            stream_handler.addFilter(DripFilter())

            Log._enable_handler('dm_output', enabled, stream_handler)
        elif not enabled:
            Log._enable_handler('dm_output', enabled)

    @staticmethod
    def enable_debug_output(enabled=True, new_stream=None):
        ''' Enables tracking of records in _debug_buffer. '''
        if enabled:
            debug_handler = logging.StreamHandler(new_stream or Log.DebugStream())
            debug_handler.setLevel(logging.DEBUG)
            Log._logger.setLevel(logging.DEBUG)
            Log._enable_handler('debug_output', enabled, debug_handler)
            print("Debug logging enabled.")
        else:
            Log._enable_handler('debug_output', False)

    @staticmethod
    def _enable_handler(name, enabled, new_handler=None):
        """
        Updates the status of a handler with the logger,
        and also updates the handler if given a new_handler.
        """
        handler, is_enabled = Log._handlers.get(name, (None, False))
        # Temporarily detach current handler from logger
        if is_enabled:
            Log._logger.removeHandler(handler)
        # Switch handler if new one is given
        if new_handler:
            if handler:
                handler.close()
            handler = new_handler
        # Update handler in dictionary
        Log._handlers[name] = (handler, enabled)

        if enabled:
            # Reattach or establish handler and return it
            Log._logger.addHandler(handler)
            return handler
        else:
            # The handler was disabled, but return whatever
            # is in the handler dictionary
            return handler

    @staticmethod
    def info(place, msg, *args, **kwargs):
        ''' Normal reporting '''
        Log._logger.info(Log._msg(place, msg), *args, **kwargs)

    @staticmethod
    def warning(place, msg, *args, **kwargs):
        ''' Problem reporting '''
        Log._logger.warning(Log._msg(place, msg), *args, *kwargs)

    @staticmethod
    def error(place, msg, *args, **kwargs):
        ''' Exception reporting '''
        Log._logger.error(Log._msg(place, msg), *args, *kwargs)

    @staticmethod
    def debug(place, msg, *args, **kwargs):
        ''' Debug info '''
        Log._logger.debug(Log._msg(place, msg), *args, *kwargs)

    @staticmethod
    def _msg(place, msg):
        ''' Joins the place and msg strings together '''
        return "{:19.18}{}".format(place, msg)

class LogSender:
    """
    Acts as a delegate container so that the logger module
    can send log output over Twitter to the master account.
    """
    def __init__(self, send_method):
        ''' Attach the send_method that will be called for write() '''
        self.send_method = send_method

    def write(self, text):
        ''' If the text is substantial, forward it '''
        if len(text) > 1: #This prevents unnecessary terminators from being sent

            self.send_method(text)

class DripFilter(logging.Filter):
    """Restricts too verbose logging by establishing a logging speed limit by level.
    KeyErrors are understood to be unrestricted"""
    TICK_SPEED = {
        logging.DEBUG: timedelta(days=1),
        logging.INFO: timedelta(hours=1),
        logging.WARNING: timedelta(minutes=1)
    }
    LAST_SEND = {
        logging.DEBUG: datetime(year=1989, month=1, day=1),
        logging.INFO: datetime(year=1989, month=1, day=1),
        logging.WARNING: datetime(year=1989, month=1, day=1)
    }

    def filter(self, record):
        """Returns true if the record text is substantial and
        the speed limit has not been exceeded.
        """
        try:
            lvl = record.levelno
        except AttributeError:
            print("Logging: Given record has no level attribute: " + str(record))
            lvl = logging.DEBUG

        okay = False
        try:
            nxtime = DripFilter.LAST_SEND[lvl] + DripFilter.TICK_SPEED[lvl]
            if nxtime > datetime.now():
                okay = True
        except KeyError:
            okay = True
        
        if okay:
            DripFilter.LAST_SEND[lvl] = datetime.now()
        
        return okay






