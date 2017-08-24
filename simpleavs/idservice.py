""" ID related helpers """

from __future__ import absolute_import
from __future__ import unicode_literals
import calendar
import time


class IdService(object):
    """ id generator which tracks number of IDs generated """

    def __init__(self, message_count=1, dialog_count=1):
        self._message_count = message_count
        self._dialog_count = dialog_count
        self._start_time = calendar.timegm(time.gmtime())

    def get_new_message_id(self):
        """ Gets a unique message_id for each message sent to the server """
        message_id = 'avs-message-id-%d-%d' % (
            self._start_time, self._message_count)

        self._message_count += 1

        return message_id

    def get_new_dialog_id(self):
        """ Gets a unique dialog_id for each message sent to the server """
        dialog_id = "avs-dialog-id-%d-%d" % (
            self._start_time, self._dialog_count)

        self._dialog_count += 1

        return dialog_id
