''' General logging wrapper for modules '''
import logging
from queue import Queue

class Log:
    ''' Wrapper for LOGGER '''

    _handlers = {}
    _logger = logging.getLogger('Untitled: Use setup()')
    _debug_buffer = []

    @staticmethod
    def write(text):
        ''' Write streamed text to buffer '''
        if text != logging.StreamHandler.terminator:
            Log._debug_buffer.append(text)

    @staticmethod
    def setup(name, level=logging.INFO):
        ''' Initial setup; does logging.getLogger '''
        Log._logger = logging.getLogger(name)
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
            Log._enable_handler('file_output', enabled, file_handler)
        else: # Just disable it
            Log._enable_handler('file_output', enabled)

    @staticmethod
    def enable_debug_output(enabled=True):
        ''' Enables tracking of records in _debug_buffer. '''
        if enabled:
            debug_handler = logging.StreamHandler(Log)
            Log._enable_handler('debug_output', enabled, debug_handler)
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
    def _msg(place, msg):
        ''' Joins the place and msg strings together '''
        return "{:19.18}{}".format(place, msg)

    @staticmethod
    def is_text_in_debug_buffer(text=None):
        ''' Debug/testing method to show that something was logged. '''
        if Log._debug_buffer:
            if not text:
                return True
            found = False
            for record in Log._debug_buffer:
                if text in record:
                    found = True
            return found
        return False

    @staticmethod
    def clear_debug_buffer():
        ''' Clears the debug_buffer '''
        Log._debug_buffer.clear()
