from __future__ import print_function
from __future__ import absolute_import

import unittest
from unittest import TestCase, expectedFailure

from httpio import HTTPIOFile
from io import IOBase

import mock
import random
import re

from six import int2byte


# 8 MB of random data for the HTTP requests to return
DATA = b''.join(int2byte(random.randint(0, 0xFF))
                for _ in range(0, 8*1024*1024))

OTHER_DATA = b''.join(int2byte(random.randint(0, 0xFF))
                      for _ in range(0, 8*1024*1024))


class TestHTTPIOFile(TestCase):
    def setUp(self):
        self.patchers = {}
        self.mocks = {}
        self.patchers['Session'] = mock.patch("requests.Session")

        for key in self.patchers:
            self.mocks[key] = self.patchers[key].start()

        # Set up the dummy HTTP requests interface:
        _session = self.mocks['Session'].return_value
        head_response = _session.head.return_value
        head_response.headers = {'Content-Length': len(DATA),
                                 'Accept-Ranges': 'bytes'}

        self.data_source = DATA

        def _get(url, **kwargs):
            (start, end) = (None, None)
            if 'headers' in kwargs:
                if 'Range' in kwargs['headers']:
                    m = re.match(r'bytes=(\d+)-(\d+)',
                                 kwargs['headers']['Range'])
                    if m:
                        start = int(m.group(1))
                        end = int(m.group(2)) + 1

            return mock.MagicMock(content=self.data_source[start:end])

        _session.get.side_effect = _get

    def tearDown(self):
        for key in self.patchers:
            self.mocks[key] = self.patchers[key].stop()

    @expectedFailure
    def test_implements_io_base(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertIsInstance(io, IOBase)

    def test_read_gets_data(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            data = io.read(1024)
            self.assertEqual(data, DATA[0:1024])

    def test_tell_starts_at_zero(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.tell(), 0)

    def test_seek_and_tell_match(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            io.seek(1536)
            self.assertEqual(io.tell(), 1536)
            io.seek(10, whence=1)
            self.assertEqual(io.tell(), 1546)
            io.seek(-20, whence=1)
            self.assertEqual(io.tell(), 1526)
            io.seek(-20, whence=2)
            self.assertEqual(io.tell(), len(DATA) - 20)

    def test_random_access(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            io.seek(1536)
            self.assertEqual(io.read(1024), DATA[1536:2560])
            io.seek(10, whence=1)
            self.assertEqual(io.read(1024), DATA[2570:3594])
            io.seek(-20, whence=1)
            self.assertEqual(io.read(1024), DATA[3574:4598])
            io.seek(-1044, whence=2)
            self.assertEqual(io.read(1024), DATA[-1044:-20])

    def test_flush_dumps_cache(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.read(1024), DATA[:1024])
            self.data_source = OTHER_DATA
            io.seek(0)
            self.assertEqual(io.read(1024), DATA[:1024])
            io.flush()
            io.seek(0)
            self.assertEqual(io.read(1024), OTHER_DATA[:1024])


if __name__ == "__main__":
    unittest.main()
