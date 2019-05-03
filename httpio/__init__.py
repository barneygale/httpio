from __future__ import absolute_import

import re
import requests

from io import BufferedIOBase

from six import PY3
from sys import version_info

__all__ = ["open", "HTTPIOError", "HTTPIOFile"]


# The expected exception from unimplemented IOBase operations
IOBaseError = OSError if PY3 else IOError


def open(url, block_size=-1, **kwargs):
    """
    Open a URL as a file-like object

    :param url: The URL of the file to open
    :param block_size: The cache block size, or `-1` to disable caching.
    :param kwargs: Additional arguments to pass to `requests.Request()`
    :return: An `httpio.HTTPIOFile` object supporting most of the usual
        file-like object methods.
    """
    f = HTTPIOFile(url, block_size, **kwargs)
    f.open()
    return f


class HTTPIOError(IOBaseError):
    pass


class SyncHTTPIOFile(BufferedIOBase):
    def __init__(self, url, block_size=-1, **kwargs):
        super(SyncHTTPIOFile, self).__init__()
        self.url = url
        self.block_size = block_size

        self._kwargs = kwargs
        self._cursor = 0
        self._cache = {}
        self._session = None

        self.length = None

        self._closing = False

    def __repr__(self):
        status = "closed" if self.closed else "open"
        return "<%s %s %r at %s>" % (status, type(self).__name__, self.url, hex(id(self)))

    def __enter__(self):
        self.open()
        return super(SyncHTTPIOFile, self).__enter__()

    def open(self):
        self._assert_not_closed()
        if not self._closing and self._session is None:
            self._session = requests.Session()
            response = self._session.head(self.url, **self._kwargs)
            response.raise_for_status()
            try:
                self.length = int(response.headers['Content-Length'])
            except KeyError:
                raise HTTPIOError("Server does not report content length")
            if response.headers.get('Accept-Ranges', '').lower() != 'bytes':
                raise HTTPIOError("Server does not accept 'Range' headers")

    def close(self):
        self._closing = True
        self._cache.clear()
        if self._session is not None:
            self._session.close()
        super(SyncHTTPIOFile, self).close()

    def flush(self):
        self._assert_not_closed()
        self.open()
        self._cache.clear()

    def peek(self, size=-1):
        loc = self.tell()
        data = self.read1(size)
        self.seek(loc)

        return data

    def read(self, size=-1):
        return self._read_impl(size)

    def read1(self, size=-1):
        return self._read_impl(size, 1)

    def readable(self):
        return True

    def readinto(self, b):
        return self._readinto_impl(b)

    def readinto1(self, b):
        return self._readinto_impl(b, 1)

    def seek(self, offset, whence=0):
        self._assert_not_closed()
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

    def tell(self):
        self._assert_not_closed()
        self.open()
        return self._cursor

    def write(self, *args, **kwargs):
        raise HTTPIOError("Writing not supported on http resource")

    def _read_impl(self, size=-1, max_raw_reads=-1):
        self._assert_not_closed()
        self.open()

        if size < 1 or self._cursor + size > self.length:
            size = self.length - self._cursor

        if size == 0:
            return b""

        if self.block_size <= 0:
            data = self._read_raw(self._cursor, self._cursor + size)

        else:
            data = b''.join(self._read_cached(size,
                                              max_raw_reads=max_raw_reads))

        self._cursor += len(data)
        return data

    def _readinto_impl(self, b, max_raw_reads=-1):
        self._assert_not_closed()
        self.open()

        size = len(b)

        if self._cursor + size > self.length:
            size = self.length - self._cursor

        if size == 0:
            return 0

        if self.block_size <= 0:
            b[:size] = self._read_raw(self._cursor, self._cursor + size)
            return size

        else:
            n = 0
            for sector in self._read_cached(size,
                                            max_raw_reads=max_raw_reads):
                b[n:n+len(sector)] = sector
                n += len(sector)

            return n

    def _read_cached(self, size, max_raw_reads=-1):
        sector0, offset0 = divmod(self._cursor, self.block_size)
        sector1, offset1 = divmod(self._cursor + size - 1, self.block_size)
        offset1 += 1
        sector1 += 1

        # Fetch any sectors missing from the cache
        status = "".join(str(int(idx in self._cache))
                         for idx in range(sector0, sector1))
        raw_reads = 0
        for match in re.finditer("0+", status):
            if max_raw_reads >= 0 and raw_reads >= max_raw_reads:
                break

            data = self._read_raw(
                self.block_size * (sector0 + match.start()),
                self.block_size * (sector0 + match.end()))
            raw_reads += 1

            for idx in range(match.end() - match.start()):
                self._cache[sector0 + idx + match.start()] = data[
                    self.block_size * idx:
                    self.block_size * (idx + 1)]

        data = []
        for idx in range(sector0, sector1):
            if idx not in self._cache:
                break

            start = offset0 if idx == sector0 else None
            end = offset1 if idx == (sector1 - 1) else None
            data.append(self._cache[idx][start:end])

        return data

    def _read_raw(self, start, end):
        headers = {"Range": "bytes=%d-%d" % (start, end - 1)}
        headers.update(self._kwargs.get("headers", {}))
        kwargs = dict(self._kwargs)
        kwargs['headers'] = headers
        response = self._session.get(
            self.url,
            **kwargs)
        response.raise_for_status()
        return response.content

    def _assert_not_closed(self):
        if self.closed:
            raise HTTPIOError("I/O operation on closed resource")


if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    from .asyncio import AsyncHTTPIOFileContextManagerMixin

    class HTTPIOFile (SyncHTTPIOFile, AsyncHTTPIOFileContextManagerMixin):
        pass
else:
    class HTTPIOFile(SyncHTTPIOFile):
        pass
