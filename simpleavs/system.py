""" owns all System AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/system
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import json
import logging
from .eventhook import EventHook
from .objectdict import ObjectDict

_LOG = logging.getLogger(__name__)


class System(object):
    """ owns all System AVS namespace interaction """

    def __init__(self, connection):
        self._connection = connection
        self._connection.opened += self.synchronize_state
        self._connection.message_received += self._handle_message
        self.reset_user_activity_event = EventHook()
        self.exception_event = EventHook()

    def synchronize_state(self):
        """ sends a SynchronizeState event to AVS """
        header = {'namespace': 'System', 'name': 'SynchronizeState'}
        self._connection.send_event(header, include_state=True)

    def user_inactivity_report(self, user_inactive_for_secs):
        """ sends a UserInactivityReport event to AVS """
        header = {'namespace': 'System', 'name': 'UserInactivityReport'}
        payload = {'inactiveTimeInSeconds': user_inactive_for_secs}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def exception_encountered(self, unparsed_directive, error):
        """ notifies AVS of an exception on the client """
        header = {'namespace': 'System', 'name': 'ExceptionEncountered'}
        payload = {'unparsedDirective': unparsed_directive, 'error': error}

        self._connection.send_event(header, include_state=True,
                                    payload=payload)

    def _handle_reset_user_activity(self, message):
        reset_activity_request = ObjectDict({
            'raw_message': message})
        self.reset_user_activity_event(reset_activity_request)

    def _handle_avs_exception(self, message):
        exception = ObjectDict({
            'message_id': message['header']['messageId'],
            'code': message['payload']['code'],
            'description': message['payload']['description'],
            'raw_message': message
            })
        self.exception_event(exception)

    def _handle_message(self, message):
        if 'directive' not in message and 'header' in message:
            header = message['header']
        elif 'directive' in message:
            header = message['directive']['header']
        else:
            _LOG.warning('System received an unrecognised message: ' +
                         json.dumps(message))
            return

        if header['namespace'] != 'System':
            return

        name = header['name']
        _LOG.info('System received message: ' + name)

        if name == 'ResetUserInactivity':
            self._handle_reset_user_activity(message)
        elif name == 'Exception':
            self._handle_avs_exception(message)
        else:
            _LOG.warning('System received an unrecognised directive: ' +
                         json.dumps(message))
