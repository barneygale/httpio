from sys import version_info

if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    from httpio_async import AsyncHTTPIOFile, AsyncHTTPIOFileContextManagerMixin

    __all__ = ['AsyncHTTPIOFile', 'AsyncHTTPIOFileContextManagerMixin']
else:
    __all__ = []
