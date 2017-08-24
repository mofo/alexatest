""" owns all AudioPlayer AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/audioplayer
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import json
from .objectdict import ObjectDict
from .eventhook import EventHook

_LOG = logging.getLogger(__name__)


class AudioPlayer(object):
    """ owns all AudioPlayer AVS namespace interaction """
    def __init__(self, connection):
        self._connection = connection
        self._connection.message_received += self._handle_message
        self.state = {'token': None, 'offsetInMilliseconds': None,
                      'playerActivity': 'IDLE'}
        self.play_event = EventHook()
        self.stop_event = EventHook()
        self.clear_queue_event = EventHook()

    def update_state(self, token=None, offset_ms=None, player_activity=None):
        """ updates the AudioPlayer current state """
        if token:
            self.state['token'] = token

        if offset_ms is not None:
            self.state['offsetInMilliseconds'] = offset_ms

        if player_activity:
            self.state['playerActivity'] = player_activity

    def playback_started(self, token, offset_ms):
        """ notifies AVS that playback was started """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackStarted'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_nearly_finished(self, token, offset_ms):
        """ notifies AVS that client is ready for next track/buffer """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackNearlyFinished'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_finished(self, token, offset_ms):
        """ notifies AVS that client has finished playback """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackFinished'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_stopped(self, token, offset_ms):
        """ notifies AVS that client has stopped playback """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackStopped'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_paused(self, token, offset_ms):
        """ notifies AVS that client has paused playback """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackPaused'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_resumed(self, token, offset_ms):
        """ notifies AVS that client has resumed playback """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackResumed'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_failed(self, token, offset_ms, player_activity, error):
        """ notifies AVS that client has failed to playback """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackFailed'}
        payload = {'token': token,
                   'currentPlaybackState': {
                       'token': token,
                       'offsetInMilliseconds': offset_ms,
                       'playerActivity': player_activity},
                   'error': error}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def progress_report_delay_elapsed(self, token, offset_ms):
        """ updates AVS with the current track's offset """
        header = {'namespace': 'AudioPlayer',
                  'name': 'ProgressReportDelayElapsed'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def progress_report_interval_elapsed(self, token, offset_ms):  # pylint: disable=invalid-name
        """ updates AVS with the current track's offset """
        header = {'namespace': 'AudioPlayer',
                  'name': 'ProgressReportIntervalElapsed'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_stutter_started(self, token, offset_ms):
        """ notifies AVS that the client is not getting data fast enough """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackStutterStarted'}
        payload = {'token': token, 'offsetInMilliseconds': offset_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_stutter_finished(self, token, offset_ms, stutter_duration_ms):
        """ notifies AVS that the client is now getting data fast enough """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackStutterFinished'}
        payload = {'token': token,
                   'offsetInMilliseconds': offset_ms,
                   'stutterDurationInMilliseconds': stutter_duration_ms}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def playback_queue_cleared(self):
        """ notifies AVS that the playback queue was cleared """
        header = {'namespace': 'AudioPlayer',
                  'name': 'PlaybackQueueCleared'}
        self._connection.send_event(header)

    def stream_metadata_extracted(self, token, metadata):
        """ notifies AVS of the stream metadata the client extracted """
        header = {'namespace': 'AudioPlayer',
                  'name': 'StreamMetadataExtracted'}
        payload = {'token': token, 'metadata': metadata}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def _handle_play(self, message):

        print (message)

        directive = message['directive']
        header = directive['header']
        payload = directive['payload']
        #audio_data = message['attachment'].raw_data
        audio_item = payload['audioItem']
        audio_stream = audio_item['stream']
        audio_url = audio_stream['url']

        play_request = ObjectDict({
            'message_id': header['messageId'],
            'play_behavior': payload.get('playBehavior', None),
            'audio_item': payload['audioItem'],
            'raw_message': message,
            'audio_data': audio_url
            })

        if 'dialogRequestId' in header:
            play_request.dialog_request_id = header['dialogRequestId']

        self.play_event(play_request)

    def _handle_stop(self, message):
        header = message['directive']['header']
        stop_request = ObjectDict({
            'message_id': header['messageId'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            stop_request.dialog_request_id = header['dialogRequestId']

        self.stop_event(stop_request)

    def _handle_clear_queue(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        clear_request = ObjectDict({
            'message_id': header['messageId'],
            'clear_behavior': payload['clearBehavior'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            clear_request.dialog_request_id = header['dialogRequestId']

        self.clear_queue_event(clear_request)

    def _handle_message(self, message):
        if 'directive' not in message:
            return

        header = message['directive']['header']

        if header['namespace'] != 'AudioPlayer':
            return

        name = header['name']
        logging.info('AudioPlayer received directive: ' + name)

        if name == 'Play':
            self._handle_play(message)
        elif name == 'Stop':
            self._handle_stop(message)
        elif name == 'ClearQueue':
            self._handle_clear_queue(message)
        else:
            _LOG.warning('AudioPlayer received an ' +
                         'unrecognised directive: ' +
                         json.dumps(message))
