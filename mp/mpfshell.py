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

"""
2016-03-16, sw@kaltpost.de

Simple file shell for Micropython.

For usage details see the README.md
"""

import cmd
import os
import sys

from mp.mpfexp import MpFileExplorer
from mp.mpfexp import RemoteIOError
from mp.pyboard import PyboardError


class MpFileShell(cmd.Cmd):

    intro = '\n** Micropython File Shell v0.1, 2016 sw@kaltpost.de **\n'
    prompt = 'mpfs> '

    def __init__(self):

        cmd.Cmd.__init__(self)
        self.fe = None

    def __del__(self):

        self.__disconnect()

    def __error(self, msg):

        sys.stderr.write("\n" + msg + "\n\n")

    def __connect(self, port):

        try:
            self.__disconnect()
            self.fe = MpFileExplorer(port)
        except PyboardError as e:
            self.__error(str(e[-1]))

    def __disconnect(self):

        if self.fe is not None:
            try:
                self.fe.close()
                self.fe = None
            except RemoteIOError as e:
                self.__error(str(e))

    def __is_open(self):

        if self.fe is None:
            self.__error("Not connected to device. Use 'open' first.")
            return False

        return True

    def do_exit(self, args):
        """exit
        Exit this shell.
        """

        return True

    def do_open(self, args):
        """open <PORT>
        Open connection to device with given serial port.
        """

        if not len(args):
            self.__error("Missing argument: <PORT>")
        else:
            self.__connect(args)

    def do_close(self, args):
        """close
        Close connection to device.
        """

        self.__disconnect()

    def do_ls(self, args):
        """ls
        List remote files.
        """

        if self.__is_open():
            try:
                files = self.fe.ls()

                print("\nRemote files:\n")

                for f in files:
                    print(" %s" % f)

                print("")

            except IOError as e:
                self.__error(str(e))

    def do_lls(self, args):
        """lls
        List files in current local directory.
        """

        files = os.listdir(".")

        print("\nLocal files:\n")

        for f in files:
            print(" %s" % f)

        print("")

    def do_lcd(self, args):
        """lcd <TARGET DIR>
        Change current local directory to given target.
        """

        if not len(args):
            self.__error("Missing argument: <TARGET DIR>")
        else:
            try:
                os.chdir(args)
            except OSError as e:
                self.__error(str(e).split("] ")[-1])

    def do_lpwd(self, args):
        """lpwd
        Print current local directory.
        """

        print(os.getcwd())

    def do_put(self, args):
        """put <LOCAL FILE> [<REMOTE FILE>]
        Upload local file. If the second parameter is given,
        its value is used for the remote file name. Otherwise the
        remote file will be named the same as the local file.
        """

        if not len(args):
            self.__error("Missing arguments: <LOCAL FILE> [<REMOTE FILE>]")

        elif self.__is_open():
            s_args = args.split(" ")

            lfile_name = s_args[0]

            if len(s_args) > 1:
                rfile_name = s_args[1]
            else:
                rfile_name = lfile_name

            try:
                self.fe.put(lfile_name, rfile_name)
            except IOError as e:
                self.__error(str(e))

    def do_get(self, args):
        """get <REMOTE FILE> [<LOCAL FILE>]
        Download remote file. If the second parameter is given,
        its value is used for the local file name. Otherwise the
        locale file will be named the same as the remote file.
        """

        if not len(args):
            self.__error("Missing arguments: <REMOTE FILE> [<LOCAL FILE>]")
        elif self.__is_open():

            s_args = args.split(" ")

            rfile_name = s_args[0]

            if len(s_args) > 1:
                lfile_name = s_args[1]
            else:
                lfile_name = rfile_name

            try:
                self.fe.get(rfile_name, lfile_name)
            except IOError as e:
                self.__error(str(e))

    def do_rm(self, args):
        """rm <REMOTE FILE>
        Delete a remote file.
        """

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            try:
                self.fe.rm(args)
            except IOError as e:
                self.__error(str(e))

    def do_cat(self, args):
        """cat <REMOTE FILE>
        Print the contents of a remote file.
        """

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            try:
                print(self.fe.gets(args))
            except IOError as e:
                self.__error(str(e))

    def do_exec(self, args):
        """exec <STATEMENT>
        Execute a Python statement on remote.
        """

        def data_consumer(data):
            sys.stdout.write(data.strip("\x04"))

        if not len(args):
            self.__error("Missing argument: <REMOTE FILE>")
        elif self.__is_open():

            try:
                self.fe.exec_raw_no_follow(args + "\n")
                ret = self.fe.follow(None, data_consumer)

                if len(ret[-1]):
                    self.__error(ret[-1])

            except IOError as e:
                self.__error(str(e))
            except PyboardError as e:
                self.__error(str(e[-1]))


if __name__ == '__main__':
    mpfs = MpFileShell()
    mpfs.cmdloop()
