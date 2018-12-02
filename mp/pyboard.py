#!/usr/bin/env python

"""
Pyboard REPL interface
"""

import sys
import time

try:
    stdout = sys.stdout.buffer
except AttributeError:
    # Python2 doesn't have buffer attr
    stdout = sys.stdout


def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    stdout.write(b)
    stdout.flush()


class PyboardError(BaseException):
    pass


class Pyboard:
    def __init__(self, conbase):

        self.con = conbase

    def close(self):

        if self.con is not None:
            self.con.close()

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):

        data = self.con.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self.con.inWaiting() > 0:
                new_data = self.con.read(1)
                data = data + new_data
                if data_consumer:
                    data_consumer(new_data)
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def enter_raw_repl(self):

        self.con.write(b"\r\x03\x03")  # ctrl-C twice: interrupt any running program

        # flush input (without relying on serial.flushInput())
        n = self.con.inWaiting()
        while n > 0:
            self.con.read(n)
            n = self.con.inWaiting()

        if self.con.survives_soft_reset():

            self.con.write(b"\r\x01")  # ctrl-A: enter raw REPL
            data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n>")

            if not data.endswith(b"raw REPL; CTRL-B to exit\r\n>"):
                print(data)
                raise PyboardError("could not enter raw repl")

            self.con.write(b"\x04")  # ctrl-D: soft reset
            data = self.read_until(1, b"soft reboot\r\n")
            if not data.endswith(b"soft reboot\r\n"):
                print(data)
                raise PyboardError("could not enter raw repl")

            # By splitting this into 2 reads, it allows boot.py to print stuff,
            # which will show up after the soft reboot and before the raw REPL.
            data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n")
            if not data.endswith(b"raw REPL; CTRL-B to exit\r\n"):
                print(data)
                raise PyboardError("could not enter raw repl")

        else:

            self.con.write(b"\r\x01")  # ctrl-A: enter raw REPL
            data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n")

            if not data.endswith(b"raw REPL; CTRL-B to exit\r\n"):
                print(data)
                raise PyboardError("could not enter raw repl")

    def exit_raw_repl(self):
        self.con.write(b"\r\x02")  # ctrl-B: enter friendly REPL

    def follow(self, timeout, data_consumer=None):

        # wait for normal output
        data = self.read_until(1, b"\x04", timeout=timeout, data_consumer=data_consumer)
        if not data.endswith(b"\x04"):
            raise PyboardError("timeout waiting for first EOF reception")
        data = data[:-1]

        # wait for error output
        data_err = self.read_until(1, b"\x04", timeout=timeout)
        if not data_err.endswith(b"\x04"):
            raise PyboardError("timeout waiting for second EOF reception")
        data_err = data_err[:-1]

        # return normal and error output
        return data, data_err

    def exec_raw_no_follow(self, command):

        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command.encode("utf-8"))

        # check we have a prompt
        data = self.read_until(1, b">")
        if not data.endswith(b">"):
            raise PyboardError("could not enter raw repl")

        # write command
        for i in range(0, len(command_bytes), 256):
            self.con.write(command_bytes[i : min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.con.write(b"\x04")

        # check if we could exec command
        data = self.con.read(2)
        if data != b"OK":
            raise PyboardError("could not exec command")

    def exec_raw(self, command, timeout=10, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)

    def eval(self, expression):
        ret = self.exec_("print({})".format(expression))
        ret = ret.strip()
        return ret

    def exec_(self, command):
        ret, ret_err = self.exec_raw(command)
        if ret_err:
            raise PyboardError("exception", ret, ret_err)
        return ret

    def execfile(self, filename):
        with open(filename, "rb") as f:
            pyfile = f.read()
        return self.exec_(pyfile)

    def get_time(self):
        t = str(self.eval("pyb.RTC().datetime()").encode("utf-8"))[1:-1].split(", ")
        return int(t[4]) * 3600 + int(t[5]) * 60 + int(t[6])


# in Python2 exec is a keyword so one must use "exec_"
# but for Python3 we want to provide the nicer version "exec"
setattr(Pyboard, "exec", Pyboard.exec_)
