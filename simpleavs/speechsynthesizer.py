""" owns all SpeechSynthesizer AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/speechsynthesizer
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import json
from .objectdict import ObjectDict
from .eventhook import EventHook

_LOG = logging.getLogger(__name__)


class SpeechSynthesizer(object):
    """ owns all SpeechSynthesizer AVS namespace interaction """
    def __init__(self, connection):
        self._connection = connection
        self._connection.message_received += self._handle_message
        self.state = {'token': None, 'offsetInMilliseconds': None,
                      'playerActivity': None}
        self.speak_event = EventHook()

    def update_state(self, token=None, offset_ms=None, player_activity=None):
        """ updates the SpeechSynthesizer current state """
        if token:
            self.state['token'] = token

        if offset_ms is not None:
            self.state['offsetInMilliseconds'] = offset_ms

        if player_activity:
            self.state['playerActivity'] = player_activity

    def speech_started(self, token):
        """ notifies AVS Speech has started """
        header = {'namespace': 'SpeechSynthesizer',
                  'name': 'SpeechStarted'}
        payload = {'token': token}

        self._connection.send_event(header, payload=payload,
                                    include_state=False)

    def speech_finished(self, token):
        """ notifies AVS Speech has finished """
        header = {'namespace': 'SpeechSynthesizer',
                  'name': 'SpeechFinished'}
        payload = {'token': token}

        self._connection.send_event(header, payload=payload,
                                    include_state=False)

    def _handle_speak(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']
        audio_data = message['attachment']

        speak_request = ObjectDict({
            'message_id': header['messageId'],
            'url': payload['url'],
            'format': payload['format'],
            'token': payload['token'],
            'raw_message': message,
            'audio_data': audio_data
            })

        if 'dialogRequestId' in header:
            speak_request.dialog_request_id = header['dialogRequestId']

        self.speak_event(speak_request)

    def _handle_message(self, message):
        if 'directive' not in message:
            return

        header = message['directive']['header']

        if header['namespace'] != 'SpeechSynthesizer':
            return

        name = header['name']
        _LOG.info('SpeechSynthesizer received directive: ' + name)

        if name == 'Speak':
            self._handle_speak(message)
        else:
            _LOG.warning('SpeechSynthesizer received ' +
                         'an unrecognised directive: ' +
                         json.dumps(message))
