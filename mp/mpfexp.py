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

import os

from mp.pyboard import Pyboard
from mp.pyboard import PyboardError


class RemoteIOError(IOError):
    pass


class MpFileExplorer(Pyboard):

    def __init__(self, port, baudrate=115200):
        Pyboard.__init__(self, port, baudrate)

        self.dir = ""

        self.setup()

    def __del__(self):

        try:
            self.exit_raw_repl()
        except:
            pass

        try:
            self.close()
        except:
            pass

    def __fqn(self, name):

        if self.dir.endswith("/"):
            fqn = self.dir + name
        else:
            fqn = self.dir + "/" + name

        return fqn

    def teardown(self):
        self.exit_raw_repl()

    def setup(self):

        self.enter_raw_repl()
        self.exec_("import os, sys")

    def ls(self):

        files = []

        try:

            res = self.eval("os.listdir('%s')" % self.dir)
            lines = res.split("\r\n")

            for l in lines:
                if l.startswith("["):
                    files = eval(l)
                    break

        except PyboardError:
            raise RemoteIOError("Device communication failed")

        return files

    def rm(self, target):

        if target not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(target))

        try:
            self.eval("os.remove('%s')" % self.__fqn(target))
        except PyboardError:
            raise RemoteIOError("Device communication failed")

    def put(self, src, dst=None, binary=False):

        assert not binary, "Binary mode not implemented"

        f = open(src, "r")
        lines = f.readlines()
        f.close()

        if dst is None:
            dst = src

        try:

            self.exec_("f = open('%s', 'w')" % self.__fqn(dst))

            for l in lines:
                self.exec_("f.write('%s')" % l.encode("string-escape"))

            self.exec_("f.close()")

        except PyboardError:
            raise RemoteIOError("Device communication failed")

    def get(self, src, dst=None, binary=False):

        assert not binary, "Binary mode not implemented"

        if src not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(src))

        if dst is None:
            dst = src

        f = open(dst, "w")

        try:
            self.exec_("f = open('%s', 'r')" % self.__fqn(src))
            ret = self.exec_("for l in f: sys.stdout.write(l),")
        except PyboardError:
            raise RemoteIOError("Device communication failed")

        f.write(ret)
        f.close()

    def gets(self, src):

        if src not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(src))

        try:
            self.exec_("f = open('%s', 'r')" % self.__fqn(src))
            ret = self.exec_("for l in f: sys.stdout.write(l),")
        except PyboardError:
            raise RemoteIOError("Device communication failed")

        return ret

    def puts(self, dst, lines):

        try:

            self.exec_("f = open('%s', 'w')" % self.__fqn(dst))

            for l in lines:
                self.exec_("f.write('%s')" % l.encode("string-escape"))

            self.exec_("f.close()")

        except PyboardError:
            raise RemoteIOError("Device communication failed")

    def size(self, target):

        return len(self.gets(target))

    def cd(self, dir):

        if dir.startswith("/"):
            self.dir = dir
        elif dir == "..":
            self.dir, _ = os.path.split(self.dir)
        else:
            self.dir = self.__fqn(dir)

    def pwd(self):

        return self.dir

    def md(self, dir):

        if dir in self.ls():
            raise RemoteIOError("File or directory already exists: '%s'" % self.__fqn(dir))

        try:
            self.eval("os.mkdir('%s')" % self.__fqn(dir))
        except PyboardError:
            raise RemoteIOError("Device communication failed")
