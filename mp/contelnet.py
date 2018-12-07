##
# The MIT License (MIT)
#
# Copyright (c) 2016 Stefan Wendler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
##


import sys
import telnetlib
import time
from collections import deque

from mp.conbase import ConBase, ConError


class ConTelnet(ConBase):
    def __init__(self, ip, user, password):
        ConBase.__init__(self)

        if sys.version_info < (3, 0):
            self.read = self.__read2
        else:
            self.read = self.__read3

        self.tn = telnetlib.Telnet(ip)

        if user == "":
            self.fifo = deque()
            return

        if b"Login as:" in self.tn.read_until(b"Login as:", timeout=5.0):
            self.tn.write(bytes(user.encode("ascii")) + b"\r\n")

            if b"Password:" in self.tn.read_until(b"Password:", timeout=5.0):

                # needed because of internal implementation details of the telnet server
                time.sleep(0.2)
                self.tn.write(bytes(password.encode("ascii")) + b"\r\n")

                if b"for more information." in self.tn.read_until(
                    b'Type "help()" for more information.', timeout=5.0
                ):
                    self.fifo = deque()
                    return

        raise ConError()

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.tn.close()
        except Exception:
            # the telnet object might not exist yet, so ignore this one
            pass

    def __fill_fifo(self, size):

        while len(self.fifo) < size:

            timeout_count = 0
            data = self.tn.read_eager()

            if len(data):
                self.fifo.extend(data)
            else:
                time.sleep(0.25)
                timeout_count += 1

    def __read2(self, size=1):

        self.__fill_fifo(size)

        data = b""
        while len(data) < size and len(self.fifo) > 0:
            data += self.fifo.popleft()

        return data

    def __read3(self, size=1):

        self.__fill_fifo(size)

        data = b""
        while len(data) < size and len(self.fifo) > 0:
            data += bytes([self.fifo.popleft()])

        return data

    def write(self, data):

        # print("write:", data)
        self.tn.write(data)
        return len(data)

    def inWaiting(self):

        n_waiting = len(self.fifo)

        if not n_waiting:
            data = self.tn.read_eager()
            self.fifo.extend(data)
            return len(data)
        else:
            return n_waiting

    def survives_soft_reset(self):
        return False
