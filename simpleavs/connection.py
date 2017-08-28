""" handles all the comms with the AVS API """

from __future__ import absolute_import
from __future__ import unicode_literals
import io
import threading
import time
import logging
import json
import re
import requests
from hyper import HTTP20Connection
from hyper.http20.exceptions import HTTP20Error
from .eventhook import EventHook
from .objectdict import ObjectDict
from .multipart import MultipartParser

_LOG = logging.getLogger(__name__)
_LOG.setLevel(0)

_FOUR_MINUTES = 240
_SIMPLE_AVS_BOUNDARY = 'simple-avs-message-boundary'

# Headers used to indicate if the content is JSON or audio
_START_JSON = ('--' + _SIMPLE_AVS_BOUNDARY +
               '\nContent-Disposition: form-data; name="metadata"\n' +
               'Content-Type: application/json; charset=UTF-8\n\n').encode()

_START_AUDIO = ('\n--' + _SIMPLE_AVS_BOUNDARY +
                '\nContent-Disposition: form-data; name="audio"\n' +
                'Content-Type: application/octet-stream\n\n').encode()


def time_now():
    """ returns the current time """
    return time.mktime(time.gmtime())


def seconds_since(seconds):
    """ returns the number of seconds elapsed since seconds """
    return time_now() - seconds


def get_boundary_from_response(response):
    """ Parses the response header and returns the boundary """
    if 'content-type' not in response.headers:
        return None

    content_type = response.headers.pop('content-type')[0]

    boundary_match = re.search(
        # e.g. multipart/related; boundary=my-magic-boundary
        r'[^;]+;\s{0,}boundary="?([^";]+)"?;?',
        content_type)

    return boundary_match.group(1)


def get_content_id(message_part):
    """ searches the message part header/content for a content ID """
    if 'Content-ID' in message_part.headers:
        content_id = message_part.headers['Content-ID'].value
        return content_id.strip(' <>').lower()

    if not message_part.is_json:
        _LOG.warning('Ignoring non-json content due to no Content-ID')
        return None

    content = message_part.json

    if 'directive' not in content or 'payload' not in content['directive']:
        return None

    if 'url' not in content['directive']['payload']:
        return None

    content_id = content['directive']['payload']['url'].replace('cid:', '')

    return content_id.strip(' <>').lower()

class ChunkIterable:
    def __init__(self, data):
        self._data = data

    def __iter__(self):
        def my_iterator():
            while True:
                ret = self._data.read(320)
                if len(ret) < 320:
                    break
                else:
                    yield ret
            yield ret
        return my_iterator()

class AvsConnection(object):
    """ handles all the comms with the AVS API """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, config, id_service, fetch_context):
        self._auth = ObjectDict(config)
        self._auth.latest_token = None
        self._auth.latest_token_time = 0
        self._stop_threads_event = threading.Event()
        self._connection = None
        self._connection_lock = threading.Lock()
        self._id_service = id_service
        self._fetch_context = fetch_context
        self._message_parts_cache = {}
        self.opened = EventHook()
        self.closed = EventHook()
        self.message_received = EventHook()

    def open(self):
        """ opens a connection to the AVS API """
        self._stop_threads_event.clear()

        with self._connection_lock:
            self._connection = HTTP20Connection(
                self._auth.url, port=443, secure=True,
                force_proto='h2', enable_push=True)

        self._start_downstream()
        self.opened()

        ping_thread = threading.Thread(target=self._ping_thread)
        ping_thread.start()

    def close(self):
        """ closes the current AVS connection """

        with self._connection_lock:
            self._stop_threads_event.set()
            try:
                self._connection.close()
                self.closed()
            except AttributeError:
                pass

    def reconnect(self):
        """ closes and re-opens the AVS API connection """
        self.close()
        time.sleep(1.2)
        self.open()

    def _start_downstream(self):
        downstream_id = self._send_request('GET', '/directives')
        downstream_response = self._get_response(downstream_id)

        if downstream_response.status != 200:
            _LOG.debug(downstream_response.read())
            raise NameError("Bad status (%s)" % downstream_response.status)

        stream = self._connection.streams[downstream_id]
        boundary = get_boundary_from_response(downstream_response)

        downstream_thread = threading.Thread(
            target=self._downstream_thread, args=[stream, boundary])
        downstream_thread.start()

    def _downstream_thread(self, stream, downstream_boundary):
        data_buff = io.BytesIO()
        multipart_parser = MultipartParser(data_buff, downstream_boundary)

        while not self._stop_threads_event.is_set():
            if stream.data:
                current_buffer_pos = data_buff.tell()
                data_buff.seek(0, io.SEEK_END)
                data_buff.write(b''.join(stream.data))
                data_buff.seek(current_buffer_pos)
                stream.data = []

            message_part = multipart_parser.get_next_part()

            if not message_part:
                time.sleep(0.5)
                continue

            self._process_message_parts([message_part])

    def _process_merge_parts(self, content_id, message_part):
        cached_part = self._message_parts_cache[content_id]
        del self._message_parts_cache[content_id]
        json_message = None

        if message_part.is_json and cached_part.is_json:
            _LOG.warning('Recieved json message parts with same ' +
                         'Content-ID (treating seperatly)')
            self.message_received(cached_part.json)
            self.message_received(message_part.json)
        elif cached_part.is_json and not message_part.is_json:
            json_message = cached_part.json
            json_message['attachment'] = message_part.raw_data
        elif message_part.is_json and not cached_part.is_json:
            json_message = message_part.json
            json_message['attachment'] = cached_part.raw_data
        else:
            _LOG.warning('Recieved non-json message parts with ' +
                         'same Content-ID (ignoring)')

        if json_message:
            self.message_received(json_message)

    def _process_message_parts(self, message_parts):
        for message_part in message_parts:

            content_id = get_content_id(message_part)

            if not content_id:
                if message_part.is_json:
                    self.message_received(message_part.json)
                else:
                    _LOG.warning('Can not handle non-json message ' +
                                 'without Content-ID')
            elif content_id in self._message_parts_cache:
                self._process_merge_parts(content_id, message_part)
            else:
                self._message_parts_cache[content_id] = message_part

    def _ping_thread(self):
        while not self._stop_threads_event.is_set():
            try:
                stream_id = self._send_request(
                    'GET', '/ping', path_version=False)
                data = self._get_response(stream_id)
            except HTTP20Error as http_err:
                _LOG.warning('Ping not successful: ' + http_err)
                self.reconnect()
                break

            if data.status != 204:
                _LOG.warning('Ping not successful: ' + data.status)
                self.reconnect()
                break

            start_sleep_time = seconds_since(0)

            while (not self._stop_threads_event.is_set() and
                   seconds_since(start_sleep_time) < _FOUR_MINUTES):
                time.sleep(1)

    def _get_current_token(self):
        """ A token is required for authentication purposes
            on any request send to the AVS. This function uses the
            refresh_token provided by the configuration file to
            get an up to date communication token. This is
            necessary since the token expires every 3600 seconds.
            A new token is requested every 3570 seconds.

        :return: a valid token
        """
        if (self._auth.latest_token is None or
                seconds_since(self._auth.latest_token_time) > 3570):
            payload = {
                'client_id': self._auth.client_id,
                'client_secret': self._auth.client_secret,
                'refresh_token': self._auth.refresh_token,
                'grant_type': 'refresh_token',
            }

            auth_url = "https://api.amazon.com/auth/o2/token"
            auth_response = requests.post(auth_url, data=payload)
            auth_json = json.loads(auth_response.text)
            token = auth_json['access_token']

            self._auth.latest_token = token
            self._auth.latest_token_time = time_now()
        else:
            token = self._auth.latest_token

        return token

    def _get_response(self, stream_id):
        with self._connection_lock:
            result = self._connection.get_response(stream_id)

        return result

    def _send_request(self, method, path, body=None, path_version=True):
        headers = {
            'authorization': 'Bearer %s' % self._get_current_token(),
            'content-type': 'multipart/form-data; boundary=%s' %
                            _SIMPLE_AVS_BOUNDARY
        }

        if path_version:
            path = '/v20160207' + path

        with self._connection_lock:
            stream_id = self._connection.request(
                method, path, headers=headers, body=body)

        return stream_id

    def _process_response(self, response):
        boundary = get_boundary_from_response(response)

        if not boundary:
            return None

        response_stream = io.BytesIO(response.read())
        multipart_parser = MultipartParser(response_stream, boundary)
        message_parts = []

        while True:
            message_part = multipart_parser.get_next_part()

            if not message_part:
                break

            message_parts.append(message_part)

        if message_parts:
            self._process_message_parts(message_parts)

    def send_event(self, header, include_state, payload=None,
                   audio=None):
        """ sends an event to AVS """
        if payload is None:
            payload = {}

        header['messageId'] = self._id_service.get_new_message_id()

        body_dict = {
            'event': {
                'header': header,
                'payload': payload
            }
        }

        if include_state:
            body_dict['context'] = self._fetch_context()

        body_string = _START_JSON + json.dumps(body_dict).encode()

        if audio is not None:
            body_string += _START_AUDIO + audio

        body_string += ("--" + _SIMPLE_AVS_BOUNDARY + "--").encode()

        _LOG.info('Sending event %s from %s',
                  header['name'], header['namespace'])

        print ('Sending event :' + header['name'] + ' from :' + header['namespace'])

        stream_id = self._send_request('POST', '/events', body=body_string)
        response = self._get_response(stream_id)

        self._process_response(response)
