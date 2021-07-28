import asyncio
from unittest import TestCase
from unittest import mock

from httpio import HTTPIOFile

import re
import warnings

from io import SEEK_CUR, SEEK_END

from random_source_data import DATA, OTHER_DATA, ASCII_DATA, ASCII_LINES


def async_func(f):
    async def __inner(*args, **kwargs):
        return f(*args, **kwargs)
    return __inner


IOBaseError = OSError


class HTTPException(Exception):
    pass


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
        loop.set_debug(True)
        E = None
        warns = []

        try:
            with warnings.catch_warnings(record=True) as warns:
                loop.run_until_complete(f(*args, **kwargs))

        except AssertionError as e:
            E = e
        except Exception as e:
            E = e

        for w in warns:
            warnings.showwarning(w.message,
                                 w.category,
                                 w.filename,
                                 w.lineno)
        if E is None:
            args[0].assertEqual(len(warns), 0,
                                msg="asyncio subsystem generated warnings due to unawaited coroutines")
        else:
            raise E

    return __inner


class TestAsyncHTTPIOFile(TestCase):
    def setUp(self):
        self.patchers = {}
        self.mocks = {}
        self.patchers['ClientSession'] = mock.patch("aiohttp.ClientSession")

        for key in self.patchers:
            self.mocks[key] = self.patchers[key].start()

        self.session = AsyncContextManagerMock()
        self.mocks['ClientSession'].return_value = self.session
        self.session.async_context_object = self.session

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

        self.session.head.side_effect = _head

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
                    async_context_object=mock.MagicMock(status_code=200,
                                                        read=mock.MagicMock(
                                                            side_effect=async_func(
                                                                lambda: self.data_source[start:end]))))
            else:
                return AsyncContextManagerMock(
                    async_context_object=mock.MagicMock(
                        status_code=self.error_code,
                        raise_for_status=mock.MagicMock(side_effect=HTTPException)))
        self.session.get.side_effect = _get

    def tearDown(self):
        for key in self.patchers:
            self.mocks[key] = self.patchers[key].stop()

    @async_test
    async def test_throws_exception_when_head_returns_error(self):
        self.error_code = 404
        with self.assertRaises(HTTPException):
            async with HTTPIOFile('http://www.example.com/test/', 1024):
                pass

    @async_test
    async def test_read_after_close_fails(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            pass
        with self.assertRaises(IOBaseError):
            await io.read()

    @async_test
    async def test_closed(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(hasattr(io, 'closed'))
            self.assertFalse(io.closed)
        self.assertTrue(io.closed)

    @async_test
    async def test_flush_dumps_cache(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.read(1024), DATA[:1024])
            self.data_source = OTHER_DATA
            await io.seek(0)
            self.assertEqual(await io.read(1024), DATA[:1024])
            await io.flush()
            await io.seek(0)
            self.assertEqual(await io.read(1024), OTHER_DATA[:1024])

    @async_test
    async def test_peek(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1500)
            data = await io.peek(1024)
            self.assertEqual(data, DATA[1500:1500 + 1024])
            self.assertEqual(await io.tell(), 1500)

    @async_test
    async def test_read_gets_data(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    @async_test
    async def test_read_gets_data_without_buffering(self):
        async with HTTPIOFile('http://www.example.com/test/') as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    @async_test
    async def test_throws_exception_when_get_returns_error(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.error_code = 404
            with self.assertRaises(HTTPException):
                await io.read(1024)
            self.assertEqual(await io.tell(), 0)

    @async_test
    async def test_read1(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1024)
            await io.read(1024)
            await io.seek(0)

            self.session.reset_mock()
            data = await io.read1()
            self.session.get.assert_called_once()

            self.assertEqual(data, DATA[:2048])
            await io.seek(1536)

    @async_test
    async def test_readable(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(await io.readable())

    @async_test
    async def test_readinto(self):
        b = bytearray(1536)
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.readinto(b), len(b))
            self.assertEqual(bytes(b), DATA[:1536])

    @async_test
    async def test_readinto1(self):
        b = bytearray(len(DATA))
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1024)
            await io.read(1024)
            await io.seek(0)

            self.session.reset_mock()
            self.assertEqual(await io.readinto1(b), 2048)
            self.session.get.assert_called_once()

            self.assertEqual(b[:2048], DATA[:2048])
            await io.seek(1536)

            self.session.reset_mock()
            self.assertEqual(await io.readinto1(b), len(DATA) - 1536)
            self.session.get.assert_called_once()

            self.assertEqual(b[:len(DATA) - 1536], DATA[1536:])

    @async_test
    async def test_readline(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual((await io.readline()).decode('ascii'),
                             ASCII_LINES[0])

    @async_test
    async def test_readlines(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual([line.decode('ascii') async for line in io.readlines()],
                             [line for line in ASCII_LINES])

    @async_test
    async def test_aiter(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual([line.decode('ascii') async for line in io],
                             [line for line in ASCII_LINES])

    @async_test
    async def test_tell_starts_at_zero(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.tell(), 0)

    @async_test
    async def test_seek_and_tell_match(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.seek(1536), 1536)
            self.assertEqual(await io.tell(), 1536)

            self.assertEqual(await io.seek(10, whence=SEEK_CUR), 1546)
            self.assertEqual(await io.tell(), 1546)

            self.assertEqual(await io.seek(-20, whence=SEEK_CUR), 1526)
            self.assertEqual(await io.tell(), 1526)

            self.assertEqual(await io.seek(-20, whence=SEEK_END), len(DATA) - 20)
            self.assertEqual(await io.tell(), len(DATA) - 20)

    @async_test
    async def test_random_access(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1536)
            self.assertEqual(await io.read(1024), DATA[1536:2560])
            await io.seek(10, whence=SEEK_CUR)
            self.assertEqual(await io.read(1024), DATA[2570:3594])
            await io.seek(-20, whence=SEEK_CUR)
            self.assertEqual(await io.read(1024), DATA[3574:4598])
            await io.seek(-1044, whence=SEEK_END)
            self.assertEqual(await io.read(1024), DATA[-1044:-20])

    @async_test
    async def test_seekable(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(await io.seekable())
