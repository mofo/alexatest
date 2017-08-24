""" http://stackoverflow.com/questions/1092531/event-system-in-python """

from __future__ import absolute_import
from __future__ import unicode_literals
import threading


class EventHook(object):
    """ simple threadsafe event handling bucket """

    def __init__(self):
        self._handlers = set()
        self._lock = threading.Lock()

    def handle(self, handler):
        """ adds a handler for the event """
        with self._lock:
            self._handlers.add(handler)

        return self

    def unhandle(self, handler):
        """ removes a handler for the event """
        try:
            with self._lock:
                self._handlers.remove(handler)
        except:
            raise ValueError('Handler not found')

        return self

    def fire(self, *args, **kargs):
        """ triggers each of the handlers for the event """
        with self._lock:
            handlers = self._handlers.copy()

        for handler in handlers:
            handler(*args, **kargs)

    def get_handler_count(self):
        """ returns the number of handlers for the event """
        with self._lock:
            handler_count = len(self._handlers)

        return handler_count

    def clear(self):
        """ removes all handlers for the event """
        with self._lock:
            self._handlers.clear()

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__ = get_handler_count
