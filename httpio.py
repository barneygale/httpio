import re
import requests


def open(url, block_size=-1, **kwargs):
    """
    Open a URL as a file-like object

    :param url: The URL of the file to open
    :param block_size: The cache block size, or `-1` to disable caching.
    :param kwargs: Additional arguments to pass to `requests.Request()`
    :return: An `httpio.HTTPIOFile` object supporting most of the usual
        file-like object methods.
    """
    return HTTPIOFile(url, block_size, **kwargs)


class HTTPIOError(Exception):
    pass


class HTTPIOFile(object):
    def __init__(self, url, block_size=-1, **kwargs):
        self.url = url
        self.block_size = block_size
        self.closed = False

        self._kwargs = kwargs
        self._cursor = 0
        self._cache = {}
        self._session = requests.Session()

        response = self._session.head(self.url, **kwargs)
        response.raise_for_status()
        try:
            self.length = int(response.headers['Content-Length'])
        except KeyError:
            raise HTTPIOError("Server does not report content length")
        if response.headers.get('Accept-Ranges', '').lower() != 'bytes':
            raise HTTPIOError("Server does not accept 'Range' headers")

    def __repr__(self):
        status = "closed" if self.closed else "open"
        return "<%s HTTPIOFile %r at %s>" % (status, self.url, hex(id(self)))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if not self.closed:
            self._session.close()
            self._cache.clear()
            self.closed = True

    def flush(self):
        self._assert_open()
        self._cache.clear()

    def read(self, size=-1):
        self._assert_open()

        if size < 1 or self._cursor + size > self.length:
            size = self.length - self._cursor

        if size == 0:
            return b""

        if self.block_size <= 0:
            data = self._read_raw(self._cursor, self._cursor + size)

        else:
            sector0, offset0 = divmod(self._cursor, self.block_size)
            sector1, offset1 = divmod(self._cursor + size - 1, self.block_size)
            offset1 += 1
            sector1 += 1

            # Fetch any sectors missing from the cache
            status = "".join(str(int(idx in self._cache))
                             for idx in range(sector0, sector1))
            for match in re.finditer("0+", status):
                data = self._read_raw(
                    self.block_size * (sector0 + match.start()),
                    self.block_size * (sector0 + match.end()))

                for idx in range(match.end() - match.start()):
                    self._cache[sector0 + idx + match.start()] = data[
                        self.block_size * idx:
                        self.block_size * (idx + 1)]

            data = []
            for idx in range(sector0, sector1):
                start = offset0 if idx == sector0 else None
                end = offset1 if idx == (sector1 - 1) else None
                data.append(self._cache[idx][start:end])

            data = b"".join(data)

        self._cursor += size
        return data

    def seek(self, offset, whence=0):
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

    def tell(self):
        self._assert_open()
        return self._cursor

    def _read_raw(self, start, end):
        headers = {"Range": "bytes=%d-%d" % (start, end - 1)}
        response = self._session.get(
            self.url,
            headers=headers,
            **self._kwargs)
        return response.content

    def _assert_open(self):
        if self.closed:
            raise HTTPIOError("I/O operation on closed resource")
