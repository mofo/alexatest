""" owns all Speaker AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/speaker
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import json
from .objectdict import ObjectDict
from .eventhook import EventHook

_LOG = logging.getLogger(__name__)


class Speaker(object):
    """ owns all Speaker AVS namespace interaction """
    def __init__(self, connection):
        self._connection = connection
        self._connection.message_received += self._handle_message
        self.state = {'volume': 50, 'muted': False}
        self.set_volume_event = EventHook()
        self.adjust_volume_event = EventHook()
        self.set_mute_event = EventHook()

    def update_state(self, volume=None, muted=None):
        """ updates Speaker current state """
        if volume is not None:
            self.state['volume'] = volume

        if muted is not None:
            self.state['muted'] = muted

    def volume_changed(self, volume, muted):
        """ notifies AVS that Set/AdjustVolume directive is completed """
        header = {'namespace': 'Speaker',
                  'name': 'VolumeChanged'}
        payload = {'volume': volume, 'muted': muted}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def mute_changed(self, volume, muted):
        """ notifies AVS that SetMute directive is completed """
        header = {'namespace': 'Speaker',
                  'name': 'MuteChanged'}
        payload = {'volume': volume, 'muted': muted}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def _handle_set_volume(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        volume_request = ObjectDict({
            'message_id': header['messageId'],
            'volume': payload['volume'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            volume_request.dialog_request_id = header['dialogRequestId']

        self.set_volume_event(volume_request)

    def _handle_adjust_volume(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        volume_request = ObjectDict({
            'message_id': header['messageId'],
            'volume': payload['volume'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            volume_request.dialog_request_id = header['dialogRequestId']

        self.adjust_volume_event(volume_request)

    def _handle_set_mute(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        mute_request = ObjectDict({
            'message_id': header['messageId'],
            'mute': payload['mute'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            mute_request.dialog_request_id = header['dialogRequestId']

        self.set_mute_event(mute_request)

    def _handle_message(self, message):
        if 'directive' not in message:
            return

        header = message['directive']['header']

        if header['namespace'] != 'Speaker':
            return

        name = header['name']
        _LOG.info('Speaker received directive: ' + name)

        if name == 'SetVolume':
            self._handle_set_volume(message)
        elif name == 'AdjustVolume':
            self._handle_adjust_volume(message)
        elif name == 'SetMute':
            self._handle_set_mute(message)
        else:
            _LOG.warning('Speaker received an unrecognised directive: ' +
                         json.dumps(message))
