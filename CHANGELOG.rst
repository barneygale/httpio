== 0.3.0 ==

* Addition of asyncio compatible interface for use in python versions 3.6 and above
* Testing in python 3.7 using tox

== 0.2.0 ==

* HTTPIOFile descends from io.BufferedIOBase and implements the full protocol
  specified for that class
* HTTPIOFile has a peek method similar to io.BufferedReader

== 0.1.4 ==

* Added unittests
* Fixed bug that caused file location pointer to advance twice on some reads
* Fixed bug that caused some reads to return more data than intended
