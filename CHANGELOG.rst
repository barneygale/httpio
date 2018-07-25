== 0.2.0 ==

* HTTPIOFile descends from io.BufferedIOBase and implements the full protocol
  specified for that class
* HTTPIOFile has a peek method similar to io.BufferedReader

== 0.1.4 ==

* Added unittests
* Fixed bug that caused file location pointer to advance twice on some reads
* Fixed bug that caused some reads to return more data than intended
