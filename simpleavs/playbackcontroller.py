""" owns all PlaybackController AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/playbackcontroller
"""

from __future__ import unicode_literals


class PlaybackController(object):
    """ owns all PlaybackController AVS namespace interaction """
    def __init__(self, connection):
        self._connection = connection

    def play_command_issued(self):
        """ notifies AVS that user started/resumed playback """
        header = {'namespace': 'PlaybackController',
                  'name': 'PlayCommandIssued'}

        self._connection.send_event(header, include_state=True)

    def pause_command_issued(self):
        """ notifies AVS that user paused playback """
        header = {'namespace': 'PlaybackController',
                  'name': 'PauseCommandIssued'}

        self._connection.send_event(header, include_state=True)

    def next_command_issued(self):
        """ notifies AVS that user skips to next track """
        header = {'namespace': 'PlaybackController',
                  'name': 'NextCommandIssued'}

        self._connection.send_event(header, include_state=True)

    def previous_command_issued(self):
        """ notifies AVS that user skips to previous track """
        header = {'namespace': 'PlaybackController',
                  'name': 'PreviousCommandIssued'}

        self._connection.send_event(header, include_state=True)
