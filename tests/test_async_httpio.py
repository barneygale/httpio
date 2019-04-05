import asyncio
import unittest
from unittest import TestCase

from httpio.async import AsyncHTTPIOFile

import mock
import random
import re

from io import SEEK_CUR, SEEK_END


def async_func(f):
    async def __inner(*args, **kwargs):
        return f(*args, **kwargs)
    return __inner


# 8 MB of random data for the HTTP requests to return
DATA = bytes(random.randint(0, 0xFF)
             for _ in range(0, 8*1024*1024))

OTHER_DATA = bytes(random.randint(0, 0xFF)
                   for _ in range(0, 8*1024*1024))

ASCII_LINES = ["Line0\n",
               "Line the first\n",
               "Line Returns\n",
               "Line goes forth"]
ASCII_DATA = b''.join(line.encode('ascii') for line in ASCII_LINES)


IOBaseError = OSError


class AsyncContextManagerMock(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(AsyncContextManagerMock, self).__init__(*args, **kwargs)

    async def __aenter__(self):
        return self.async_context_object

    async def __aexit__(self, *args, **kwargs):
        pass


def async_test(f):
    def __inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f(*args, **kwargs))

    return __inner

class TestAsyncHTTPIOFile(TestCase):
    def setUp(self):
        self.patchers = {}
        self.mocks = {}
        self.patchers['ClientSession'] = mock.patch("aiohttp.ClientSession")

        for key in self.patchers:
            self.mocks[key] = self.patchers[key].start()

        session = AsyncContextManagerMock()
        self.mocks['ClientSession'].return_value = session
        session.async_context_object = session

        self.data_source = DATA
        self.error_code = None

        def _head(url, **kwargs):
            m = AsyncContextManagerMock()
            if self.error_code is None:
                m.async_context_object.status_code = 204
                m.async_context_object.headers = {'content-length':
                                                  len(self.data_source),
                                                  'Accept-Ranges':
                                                  'bytes'}
            else:
                m.async_context_object.status_code = self.error_code
                m.async_context_object.raise_for_status = mock.MagicMock(side_effect=HTTPException)
            return m

        session.head.side_effect = _head

        def _get(*args, **kwargs):
            (start, end) = (None, None)
            if 'headers' in kwargs:
                if 'Range' in kwargs['headers']:
                    m = re.match(r'bytes=(\d+)-(\d+)',
                                 kwargs['headers']['Range'])
                    if m:
                        start = int(m.group(1))
                        end = int(m.group(2)) + 1

            if self.error_code is None:
                return AsyncContextManagerMock(
                    async_context_object=mock.MagicMock(status_code = 200,
                                                        read=mock.MagicMock(
                                                            side_effect = async_func(
                                                                lambda : self.data_source[start:end]))))
            else:
                return AsyncContextManagerMock(
                    async_context_object=mock.MagicMock(
                        status_code = self.error_code,
                        raise_for_status = mock.MagicMock(side_effect=HTTPException)))
        session.get.side_effect = _get

    def tearDown(self):
        for key in self.patchers:
            self.mocks[key] = self.patchers[key].stop()

    @async_test
    async def test_read_gets_data(self):
        async with AsyncHTTPIOFile('http://www.example.com/test/', 1024) as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    @async_test
    async def test_read_gets_data_without_buffering(self):
        async with AsyncHTTPIOFile('http://www.example.com/test/') as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    @async_test
    async def test_random_access(self):
        async with AsyncHTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1536)
            self.assertEqual(await io.read(1024), DATA[1536:2560])
            await io.seek(10, whence=SEEK_CUR)
            self.assertEqual(await io.read(1024), DATA[2570:3594])
            await io.seek(-20, whence=SEEK_CUR)
            self.assertEqual(await io.read(1024), DATA[3574:4598])
            await io.seek(-1044, whence=SEEK_END)
            self.assertEqual(await io.read(1024), DATA[-1044:-20])
