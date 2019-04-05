"""This module provides an interface for using httpio with the python3 asyncio library.

The interface is where possible as similar to the existing httpio interface as possible (and hence similar to the
file like objects of python) except that many methods are replaced with asynchronous coroutines."""

import aiohttp


async def open(url, block_size=-1, **kwargs):
    """
    Open a URL as an asynchronous file-like object

    The returned object is open, and needs to be closed when done.
    This will be handled automatically if you use it as an asynchronous context manager.

    :param url: The URL of the file to open
    :param block_size: The cache block size, or `-1` to disable caching.
    :param kwargs: Additional arguments to pass to `requests.Request()`
    :return: An `httpio.HTTPIOFile` object supporting most of the usual
        file-like object methods.
    """
    f = AsyncHTTPIOFile(session, url, block_size, **kwargs)
    await f.open()
    return f


class AsyncHTTPIOFile(object):
    """An asynchronous equivalent to httpio.HTTPIOFile.
    Sadly this class cannot descend from that one for technical reasons.
    """
    def __init__(self, url, block_size=-1, **kwargs):
        """
        :param url: The URL of the file to open
        :param block_size: The cache block size, or `-1` to disable caching.
        :param kwargs: Additional arguments to pass to `session.get`
        """
        super(AsyncHTTPIOFile, self).__init__()
        self.url = url
        self.block_size = block_size

        self._kwargs = kwargs
        self._cursor = 0
        self._cache = {}
        self._session = None

        self.length = None
        self.closed = True

    async def open(self):
        """This method has no direct equivalent in the HTTPIOFile interface, but does things which
        are the equivalent of what's done in the constructor of that class. Since constructors cannot
        be coroutines this class needs this as a seperate coroutine"""

        if self.closed:
            self._session = await aiohttp.ClientSession().__aenter__()
            async with self._session.head(self.url, **self._kwargs) as response:
                self.length = int(response.headers.get('content-length', None))
                self.closed = False

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        if not self.closed:
            await self._session.__aexit__(None, None, None)
            self._session = None
            self._cache.clear()
            self.closed = True

    async def flush(self):
        self._cache.clear()

    async def read(self, size=-1):
        return await self._read_impl(size)

    async def read1(self, size=-1):
        return await self._read_impl(size, 1)

    def readable(self):
        return True

    async def readinto(self, b):
        return await self._readinto_impl(b)

    async def readinto1(self, b):
        return await self._readinto_impl(b, 1)

    async def seek(self, offset, whence=0):
        self._assert_open()
        if whence == 0:
            self._cursor = offset
        elif whence == 1:
            self._cursor += offset
        elif whence == 2:
            self._cursor = self.length + offset
        else:
            raise HTTPIOError("Invalid argument: whence=%r" % whence)
        if not (0 <= self._cursor <= self.length):
            raise HTTPIOError("Invalid argument: cursor=%r" % self._cursor)
        return self._cursor

    def seekable(self):
        return True

    async def tell(self):
        self._assert_open()
        return self._cursor

    async def write(self, *args, **kwargs):
        raise HTTPIOError("Writing not supported on http resource")

    async def _read_impl(self, size=-1, max_raw_reads=-1):
        self._assert_open()

        if size < 1 or self._cursor + size > self.length:
            size = self.length - self._cursor

        if size == 0:
            return b""

        if self.block_size <= 0:
            data = await self._read_raw(self._cursor, self._cursor + size)

        else:
            data = b''
            async for sector in self._read_cached(size,
                                                  max_raw_reads=max_raw_reads):
                data += sector

        self._cursor += len(data)
        return data

    async def _readinto_impl(self, b, max_raw_reads=-1):
        self._assert_open()

        size = len(b)

        if self._cursor + size > self.length:
            size = self.length - self._cursor

        if size == 0:
            return 0

        if self.block_size <= 0:
            b[:size] = await self._read_raw(self._cursor, self._cursor + size)
            return size

        else:
            n = 0
            async for sector in self._read_cached(size,
                                                  max_raw_reads=max_raw_reads):
                b[n:n+len(sector)] = sector
                n += len(sector)

            return n

    async def _read_cached(self, size, max_raw_reads=-1):
        sector0, offset0 = divmod(self._cursor, self.block_size)
        sector1, offset1 = divmod(self._cursor + size - 1, self.block_size)
        offset1 += 1
        sector1 += 1

        raw_reads = 0

        data = []
        for idx in range(sector0, sector1):
            if idx not in self._cache:
                end = idx + 1
                while end < sector1 and end not in self._cache:
                    end += 1

                read_data = await self._read_raw(
                    self.block_size * idx,
                    self.block_size * end
                )
                raw_reads += 1

                for i in range(end - idx):
                    self._cache[idx + i] = read_data[
                        self.block_size * i:
                        self.block_size * (i + 1)
                    ]

            start = offset0 if idx == sector0 else None
            end = offset1 if idx == (sector1 - 1) else None
            yield self._cache[idx][start:end]

    async def _read_raw(self, start, end):
        headers = {"Range": "bytes=%d-%d" % (start, end - 1)}
        headers.update(self._kwargs.get("headers", {}))
        kwargs = dict(self._kwargs)
        kwargs['headers'] = headers
        async with self._session.get(
                self.url,
                **kwargs) as response:
            response.raise_for_status()
            return await response.read()

    def _assert_open(self):
        if self.closed:
            raise HTTPIOError("I/O operation on closed resource")
