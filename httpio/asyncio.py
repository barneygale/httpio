from sys import version_info

if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    from httpio_async import AsyncHTTPIOFile, AsyncHTTPIOFileContextManagerMixin  # noqa: F401

    __all__ = ['AsyncHTTPIOFile', 'AsyncHTTPIOFileContextManagerMixin']
else:
    __all__ = []
