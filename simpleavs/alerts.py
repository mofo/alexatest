""" owns all Alerts AVS namespace interaction

    https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/alerts
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import json
from .objectdict import ObjectDict
from .eventhook import EventHook

_LOG = logging.getLogger(__name__)


class Alerts(object):
    """ owns all Alerts AVS namespace interaction """
    def __init__(self, connection):
        self._connection = connection
        self._connection.message_received += self._handle_message
        self.state = {'allAlerts': [], 'activeAlerts': []}
        self.set_alert_event = EventHook()
        self.delete_alert_event = EventHook()

    def update_state(self, all_alerts=None, active_alerts=None):
        """ updates Alerts current state """
        if all_alerts is not None:
            self.state['allAlerts'] = all_alerts

        if active_alerts is not None:
            self.state['activeAlerts'] = active_alerts

    def set_alert_succeeded(self, token):
        """ notifies AVS that alert was set """
        header = {'namespace': 'Alerts',
                  'name': 'SetAlertSucceeded'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def set_alert_failed(self, token):
        """ notifies AVS that alert wasn't set """
        header = {'namespace': 'Alerts',
                  'name': 'SetAlertFailed'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def delete_alert_succeeded(self, token):
        """ notifies AVS that alert was set """
        header = {'namespace': 'Alerts',
                  'name': 'DeleteAlertSucceeded'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def delete_alert_failed(self, token):
        """ notifies AVS that alert wasn't set """
        header = {'namespace': 'Alerts',
                  'name': 'DeleteAlertFailed'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def alert_started(self, token):
        """ notifies AVS that alert was started """
        header = {'namespace': 'Alerts',
                  'name': 'AlertStarted'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def alert_stopped(self, token):
        """ notifies AVS that alert was stopped """
        header = {'namespace': 'Alerts',
                  'name': 'AlertStopped'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def alert_entered_foreground(self, token):
        """ notifies AVS that alert is playing in foreground """
        header = {'namespace': 'Alerts',
                  'name': 'AlertEnteredForeground'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def alert_entered_background(self, token):
        """ notifies AVS that alert has been attenuated/paused """
        header = {'namespace': 'Alerts',
                  'name': 'AlertEnteredBackground'}
        payload = {'token': token}

        self._connection.send_event(header, include_state=False,
                                    payload=payload)

    def _handle_set_alert(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        alert_request = ObjectDict({
            'message_id': header['messageId'],
            'token': payload['token'],
            'type': payload['type'],
            'scheduled_time': payload['scheduledTime'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            alert_request.dialog_request_id = header['dialogRequestId']

        self.set_alert_event(alert_request)

    def _handle_delete_alert(self, message):
        directive = message['directive']
        header = directive['header']
        payload = directive['payload']

        alert_request = ObjectDict({
            'message_id': header['messageId'],
            'token': payload['token'],
            'raw_message': message})

        if 'dialogRequestId' in header:
            alert_request.dialog_request_id = header['dialogRequestId']

        self.delete_alert_event(alert_request)

    def _handle_message(self, message):
        if 'directive' not in message:
            return

        header = message['directive']['header']

        if header['namespace'] != 'Alerts':
            return

        name = header['name']
        _LOG.info('Alerts received directive: ' + name)

        if name == 'SetAlert':
            self._handle_set_alert(message)
        elif name == 'DeleteAlert':
            self._handle_delete_alert(message)
        else:
            _LOG.warning('Alerts received an unrecognised directive: ' +
                         json.dumps(message))
