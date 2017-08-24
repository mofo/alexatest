""" owns all SpeechRecognizer AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/speechrecognizer
"""


from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import json
from .objectdict import ObjectDict
from .eventhook import EventHook

_LOG = logging.getLogger(__name__)


class SpeechRecognizer(object):
    """ owns all SpeechRecognizer AVS namespace interaction """
    def __init__(self, connection, id_service):
        self._connection = connection
        self._connection.message_received += self._handle_message
        self._id_service = id_service
        self.stop_capture_event = EventHook()
        self.expect_speech_event = EventHook()

    def recognize(self, audio_data, profile,
                  audio_format='AUDIO_L16_RATE_16000_CHANNELS_1',
                  dialog_request_id=None):
        """ sends a Recognize event to AVS """
        dialog_id = dialog_request_id or self._id_service.get_new_dialog_id()
        header = {'namespace': 'SpeechRecognizer',
                  'name': 'Recognize',
                  'dialogRequestId': dialog_id}
        payload = {'profile': profile, 'format': audio_format}

        send_event = self._connection.send_event
        send_event(header, include_state=True,
                   payload=payload, audio=audio_data)

    def expect_speech_timed_out(self):
        """ notifies AVS that ExpectSpeech directive timed out """
        header = {'namespace': 'SpeechRecognizer',
                  'name': 'ExpectSpeechTimedOut'}
        self._connection.send_event(header, include_state=False)

    def _handle_stop_capture(self, message):
        header = message['directive']['header']
        stop_request = ObjectDict({
            'message_id': header['messageId'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            stop_request.dialog_request_id = header['dialogRequestId']

        self.stop_capture_event(stop_request)

    def _handle_expect_speech(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        expect_request = ObjectDict({
            'message_id': header['messageId'],
            'timeout_in_milliseconds': payload['timeoutInMilliseconds'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            expect_request.dialog_request_id = header['dialogRequestId']

        self.expect_speech_event(expect_request)

    def _handle_message(self, message):
        if 'directive' not in message:
            return

        header = message['directive']['header']

        if header['namespace'] != 'SpeechRecognizer':
            return

        name = header['name']
        _LOG.info('SpeechRecognizer received directive: ' + name)

        if name == 'StopCapture':
            self._handle_stop_capture(message)
        elif name == 'ExpectSpeech':
            self._handle_expect_speech(message)
        else:
            _LOG.warning('SpeechRecognizer received ' +
                         'an unrecognised directive: ' +
                         json.dumps(message))
