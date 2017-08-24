""" main AVS client """

from __future__ import absolute_import
from __future__ import unicode_literals
from .alerts import Alerts
from .audioplayer import AudioPlayer
from .connection import AvsConnection
from .playbackcontroller import PlaybackController
from .speaker import Speaker
from .speechrecognizer import SpeechRecognizer
from .speechsynthesizer import SpeechSynthesizer
from .system import System
from .idservice import IdService


class AvsClient(object):
    """ main AVS client """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, config):
        self.id_service = IdService()

        config['url'] = config.get('url', 'avs-alexa-na.amazon.com')
        self._connection = AvsConnection(config, id_service=self.id_service,
                                         fetch_context=self._fetch_context)

        self.speech_recognizer = SpeechRecognizer(
            self._connection, self.id_service)
        self.speech_synthesizer = SpeechSynthesizer(self._connection)
        self.alerts = Alerts(self._connection)
        self.audio_player = AudioPlayer(self._connection)
        self.playback_controller = PlaybackController(self._connection)
        self.speaker = Speaker(self._connection)
        self.system = System(self._connection)

    def _fetch_context(self):
        alerts_state = {
            'header': {'namespace': 'Alerts',
                       'name': 'AlertsState'},
            'payload': self.alerts.state
        }

        speaker_state = {
            'header': {'namespace': 'Speaker',
                       'name': 'SpeakerState'},
            'payload': self.speaker.state
        }

        context_state = [alerts_state, speaker_state]

        if self.audio_player.state['token']:
            audio_player_state = {
                'header': {'namespace': 'AudioPlayer',
                           'name': 'PlaybackState'},
                'payload': self.audio_player.state
            }
            context_state.append(audio_player_state)

        if self.speech_synthesizer.state['token']:
            speech_synthesizer_state = {
                'header': {'namespace': 'SpeechSynthesizer',
                           'name': 'SpeechState'},
                'payload': self.speech_synthesizer.state
            }
            context_state.append(speech_synthesizer_state)

        return context_state

    def connect(self):
        """ open an HTTP/2 connection to the AVS API """
        self._connection.open()

    def disconnect(self):
        """ disconnect from the AVS API """
        self._connection.close()
