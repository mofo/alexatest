""" Minimal in-memory parser for multi-part HTTP data

    Mostly inspired from: https://github.com/defnull/multipart
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import re
import json
from io import BytesIO
from requests.structures import CaseInsensitiveDict
from .objectdict import ObjectDict

_SPECIAL_CHARS = re.escape('()<>@,;:\\"/[]?={} \t')
_QUOTED_VALUE = '"(?:\\\\.|[^"])*"'
_OPTION_VALUE = '(?:[^%s]+|%s)' % (_SPECIAL_CHARS, _QUOTED_VALUE)
_HEADER_OPTION = '(?:;|^)\\s*([^%s]+)\\s*=\\s*(%s)' % (
    _SPECIAL_CHARS, _OPTION_VALUE)

# key=value part of Content-Type style header
_REGEX_HEADER_OPTION = re.compile(_HEADER_OPTION)


def header_unquote(val):
    """ removes the quotes from a header value """
    if val[0] == val[-1] == '"':
        val = val[1:-1]

        if val[1:3] == ':\\' or val[:2] == '\\\\':
            val = val.split('\\')[-1]  # fix ie6 bug: full path --> filename

        return val.replace('\\\\', '\\').replace('\\"', '"')

    return val


def parse_options_header(header):
    """ parse out the key=value parts of an http header """
    if ';' not in header:
        return header.lower().strip(), {}

    main_value, tail = header.split(';', 1)
    options = {}

    for match in _REGEX_HEADER_OPTION.finditer(tail):
        key = match.group(1).lower()
        value = header_unquote(match.group(2))
        options[key] = value

    return main_value, options


class MultipartError(ValueError):
    """ Represents a generic multipart error """
    pass


class MultipartParser(object):
    """ Parse a multipart byte array """

    def __init__(self, stream, boundary, charset='UTF-8'):
        self._stream = stream
        self._done = []
        self._current_part = None
        self.charset = charset
        self.boundary = boundary.encode(charset)

    def get_next_part(self):
        """ returns the next available part from the message """
        for part in self._iterparse():
            self._done.append(part)

        if self._done:
            return self._done.pop(0)
        else:
            return None

    def reset_stream(self):
        """ allows the stream to be re-read if desired """
        self._stream.seek(0)

    def _line_iterator(self):
        """ Iterate over a binary stream line by line. Each line is
            returned as a (line, line_ending) tuple.
        """
        _bempty = b''
        _bcr = b'\r'
        _bnl = b'\n'
        _bcrnl = _bcr + _bnl

        buf = _bempty  # buffer for the last (partial) line

        while True:
            data = self._stream.read(4096)
            lines = (buf+data).splitlines(True)

            if not lines:
                break

            if data:
                buf = lines[-1]
                lines = lines[:-1]

            for line in lines:
                if line.endswith(_bcrnl):
                    yield line[:-2], _bcrnl
                elif line.endswith(_bnl):
                    yield line[:-1], _bnl
                elif line.endswith(_bcr):
                    yield line[:-1], _bcr
                else:
                    yield line, _bempty

            if not data:
                break

    def _iterparse(self):
        newline = None
        lines, line = self._line_iterator(), ''
        separator = b'--' + self.boundary
        terminator = b'--' + self.boundary + b'--'
        is_tail = False  # True if the last line was incomplete (cut)

        for line, newline in lines:
            if line:
                break

        if not line:
            return

        if line != separator and self._current_part:
            # stream must have received more data from last run
            is_tail = not newline  # The next line continues this one

            # ignore any leading blank lines before headers
            if line or is_tail or self._current_part.has_headers:
                self._current_part.feed(line, newline)

        if line != separator and not self._current_part:
            raise MultipartError('Stream does not start with boundary: ' +
                                 line)

        if not self._current_part:
            self._current_part = MultipartPart(charset=self.charset)

        for line, newline in lines:
            if line == terminator and not is_tail:
                self._current_part.is_last_part = True
                yield self._current_part
                break
            elif line == separator and not is_tail:
                yield self._current_part
                self._current_part = MultipartPart(charset=self.charset)
            else:
                is_tail = not newline  # The next line continues this one

                # ignore any leading blank lines before headers
                if line or is_tail or self._current_part.has_headers:
                    self._current_part.feed(line, newline)


class MultipartPart(object):
    """ represents a part of a multipart boundary message """

    def __init__(self, charset='UTF-8'):
        self._data = ObjectDict({'bytes': None, 'buf': b''})
        self._cache = ObjectDict({
            'raw_data': None, 'text': None, 'json': None})
        self._last_header = None
        self._data_charset = charset
        self.charset = charset
        self.headers = CaseInsensitiveDict()
        self.is_last_part = False

    def _clear_cache(self):
        self._cache.raw_data = None
        self._cache.text = None
        self._cache.json = None

    def feed(self, line, newline=''):
        """ adds a line of message data to the part """
        if self._data.bytes:
            return self.write_body(line, newline)

        return self.write_header(line, newline)

    def write_header(self, line, newline):
        """ adds a header line to the part """
        line = line.decode(self.charset)

        if not newline:
            raise MultipartError('Unexpected end of line in header.')

        if not line.strip():  # blank line -> end of header segment
            self.finish_headers()
        elif line[0] in ' \t' and self._last_header:
            name, value = self._last_header
            self.headers[name] = value + line.strip()
            self._last_header = None
        else:
            if ':' not in line:
                raise MultipartError('Syntax error in header: No colon.')

            name, value = line.split(':', 1)
            self.headers[name.strip()] = value.strip()
            self._last_header = (name.strip(), value.strip())

    def write_body(self, line, newline):
        """ adds a line of body data to the part """
        if not line and not newline:
            return

        self._clear_cache()
        self._data.bytes.write(self._data.buf + line)
        self._data.buf = newline

    def finish_headers(self):
        """ finishes parsing the headers and sets up data """
        parsed_headers = CaseInsensitiveDict()

        for key, value in self.headers.iteritems():
            main_value, options = parse_options_header(value)
            parsed_headers[key] = ObjectDict(options)
            parsed_headers[key].value = main_value

            if key == 'Content-Type' and 'charset' in options:
                self._data_charset = options['charset']

        self.headers = parsed_headers
        self._data.bytes = BytesIO()

    @property
    def is_json(self):
        """ returns True if it is a json based content type """
        content_type = ''

        if self.has_headers and 'Content-Type' in self.headers:
            content_type = self.headers['Content-Type'].value

        return content_type.endswith('/json')

    @property
    def has_headers(self):
        """ returns true if headers have been set """
        return len(self.headers) > 0

    @property
    def json(self):
        """ text data read as json """
        if not self.is_json:
            return None

        if self._cache.json is not None:
            return self._cache.json

        return json.loads(self.text)

    @property
    def text(self):
        """ Data decoded with the specified charset """
        if self._cache.text is not None:
            return self._cache.text

        return self.raw_data.decode(self._data_charset)

    @property
    def raw_data(self):
        """ Data without decoding """
        if self._cache.raw_data is not None:
            return self._cache.raw_data

        current_position = self._data.bytes.tell()
        self._data.bytes.seek(0)

        try:
            data = self._data.bytes.read()
        except IOError:
            raise
        finally:
            self._data.bytes.seek(current_position)

        return data
