from unittest import IsolatedAsyncioTestCase, mock

from httpio import HTTPIOFile

import aiohttp
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


class HTTPException(Exception):
    pass


class TestAsyncHTTPIOFile(IsolatedAsyncioTestCase):
    def setUp(self):
        self.patchers = {}
        self.mocks = {}
        self.patchers['ClientSession'] = mock.patch("aiohttp.ClientSession")

        for key in self.patchers:
            self.mocks[key] = self.patchers[key].start()

        self.session = mock.MagicMock()
        self.mocks['ClientSession'].return_value = self.session
        self.session.__aenter__.return_value = self.session

        self.data_source = DATA
        self.error_code = None

        def _head(url, **kwargs):
            m = mock.MagicMock(spec=aiohttp.ClientResponse)
            m.__aenter__.return_value = m
            if self.error_code is None:
                m.status_code = 204
                m.headers = {
                    'content-length': len(self.data_source),
                    'Accept-Ranges': 'bytes'
                }
            else:
                m.status_code = self.error_code
                m.raise_for_status.side_effect = HTTPException
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
                m = mock.MagicMock(status_code=200, spec=aiohttp.ClientResponse)
                m.__aenter__.return_value = m
                m.read.return_value = self.data_source[start:end]
                return m

            else:
                m = mock.MagicMock(status_code=self.error_code, spec=aiohttp.ClientResponse)
                m.raise_for_status.side_effect = HTTPException
                m.__aenter__.return_value = m
                return m

        self.session.get.side_effect = _get

    def tearDown(self):
        for key in self.patchers:
            self.mocks[key] = self.patchers[key].stop()

    async def test_throws_exception_when_head_returns_error(self):
        self.error_code = 404
        with self.assertRaises(HTTPException):
            async with HTTPIOFile('http://www.example.com/test/', 1024):
                pass

    async def test_read_after_close_fails(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            pass
        with self.assertRaises(IOBaseError):
            await io.read()

    async def test_closed(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(hasattr(io, 'closed'))
            self.assertFalse(io.closed)
        self.assertTrue(io.closed)

    async def test_flush_dumps_cache(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.read(1024), DATA[:1024])
            self.data_source = OTHER_DATA
            await io.seek(0)
            self.assertEqual(await io.read(1024), DATA[:1024])
            await io.flush()
            await io.seek(0)
            self.assertEqual(await io.read(1024), OTHER_DATA[:1024])

    async def test_peek(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            await io.seek(1500)
            data = await io.peek(1024)
            self.assertEqual(data, DATA[1500:1500 + 1024])
            self.assertEqual(await io.tell(), 1500)

    async def test_read_gets_data(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    async def test_read_gets_data_without_buffering(self):
        async with HTTPIOFile('http://www.example.com/test/') as io:
            data = await io.read(1024)
        self.assertEqual(data, DATA[0:1024])

    async def test_throws_exception_when_get_returns_error(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.error_code = 404
            with self.assertRaises(HTTPException):
                await io.read(1024)
            self.assertEqual(await io.tell(), 0)

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

    async def test_readable(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(await io.readable())

    async def test_readinto(self):
        b = bytearray(1536)
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.readinto(b), len(b))
            self.assertEqual(bytes(b), DATA[:1536])

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

    async def test_readline(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual((await io.readline()).decode('ascii'),
                             ASCII_LINES[0])

    async def test_readlines(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual([line.decode('ascii') async for line in io.readlines()],
                             [line for line in ASCII_LINES])

    async def test_aiter(self):
        self.data_source = ASCII_DATA
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual([line.decode('ascii') async for line in io],
                             [line for line in ASCII_LINES])

    async def test_tell_starts_at_zero(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(await io.tell(), 0)

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

    async def test_seekable(self):
        async with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(await io.seekable())
