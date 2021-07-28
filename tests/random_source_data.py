import random
from six import int2byte

# 8 MB of random data for the HTTP requests to return
DATA = b''.join(int2byte(random.getrandbits(8))
                for _ in range(0, 8*1024*1024))

OTHER_DATA = b''.join(int2byte(random.getrandbits(8))
                      for _ in range(0, 8*1024*1024))

ASCII_LINES = ["Line0\n",
               "Line the first\n",
               "Line Returns\n",
               "Line goes forth"]
ASCII_DATA = b''.join(line.encode('ascii') for line in ASCII_LINES)
