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
import re
import binascii
import getpass

from mp.pyboard import Pyboard
from mp.pyboard import PyboardError
from mp.conserial import ConSerial
from mp.contelnet import ConTelnet
from mp.conwebsock import ConWebsock
from mp.conbase import ConError


class RemoteIOError(IOError):
    pass


class MpFileExplorer(Pyboard):
    BIN_CHUNK_SIZE = 64

    def __init__(self, constr):
        """
        ser:/dev/ttyUSB1,115200
        tn:192.168.1.101,23
        ws:192.168.1.102,8080

        :param constr:
        """

        try:
            Pyboard.__init__(self, self.__con_from_str(constr))
        except Exception as e:
            raise ConError(e)

        self.dir = "/"
        self.sysname = None
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

    def __con_from_str(self, constr):

        con = None

        proto, target = constr.split(":")
        params = target.split(",")

        if proto.strip(" ") == "ser":
            port = params[0].strip(" ")

            if len(params) > 1:
                baudrate = int(params[1].strip(" "))
            else:
                baudrate = 115200

            # print("serial connection to: %s, %d" % (port, baudrate))
            con = ConSerial(port=port, baudrate=baudrate)

        elif proto.strip(" ") == "tn":

            host = params[0].strip(" ")

            if len(params) > 1:
                login = params[1].strip(" ")
            else:
                print("")
                login = raw_input("telnet login : ")

            if len(params) > 2:
                passwd = params[2].strip(" ")
            else:
                passwd = getpass.getpass("telnet passwd: ")

            # print("telnet connection to: %s, %s, %s" % (host, login, passwd))
            con = ConTelnet(ip=host, user=login, password=passwd)

        elif proto.strip(" ") == "ws":

            host = params[0].strip(" ")

            if len(params) > 1:
                passwd = params[1].strip(" ")
            else:
                passwd = getpass.getpass("webrepl passwd: ")

            con = ConWebsock(host, passwd)

        return con

    def __fqn(self, name):

        if self.dir.endswith("/"):
            fqn = self.dir + name
        else:
            fqn = self.dir + "/" + name

        return fqn

    def __set_sysname(self):
        self.sysname = self.eval("os.uname()[0]").decode('utf-8')

    def close(self):
        Pyboard.close(self)
        self.dir = "/"

    def teardown(self):
        self.exit_raw_repl()
        self.sysname = None

    def setup(self):

        self.enter_raw_repl()
        self.exec_("import os, sys, ubinascii")
        self.__set_sysname()

    def ls(self, add_files=True, add_dirs=True, add_details=False):

        files = []

        try:

            res = self.eval("os.listdir('%s')" % self.dir)
            tmp = eval(res)

            if add_dirs:
                for f in tmp:
                    try:
                        self.eval("os.listdir('%s/%s')" % (self.dir, f))
                        if add_details:
                            files.append((f, 'D'))
                        else:
                            files.append(f)
                    except PyboardError:
                        if self.sysname == "WiPy" and self.dir == "/":
                            # for the WiPy, assume that all entries in the root of th FS
                            # are mount-points, and thus treat them as directories
                            if add_details:
                                files.append((f, 'D'))
                            else:
                                files.append(f)

            if add_files and not (self.sysname == "WiPy" and self.dir == "/"):
                for f in tmp:
                    try:
                        self.eval("os.listdir('%s/%s')" % (self.dir, f))
                    except PyboardError:
                        if add_details:
                            files.append((f, 'F'))
                        else:
                            files.append(f)

        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

        return files

    def rm(self, target):

        if target not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(target))

        try:
            self.eval("os.remove('%s')" % self.__fqn(target))
        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

    def mrm(self, pat, verbose=False):

        files = self.ls(add_dirs=False)
        find = re.compile(pat)

        for f in files:
            if find.match(f):
                if verbose:
                    print(" * rm %s" % f)

                self.rm(f)

    def put(self, src, dst=None):

        f = open(src, "rb")
        data = f.read()
        f.close()

        if dst is None:
            dst = src

        try:

            self.exec_("f = open('%s', 'wb')" % self.__fqn(dst))

            while True:
                c = binascii.hexlify(data[:self.BIN_CHUNK_SIZE])
                if not len(c):
                    break

                self.exec_("f.write(ubinascii.unhexlify('%s'))" % c.decode('utf-8'))
                data = data[self.BIN_CHUNK_SIZE:]

            self.exec_("f.close()")

        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

    def mput(self, src_dir, pat, verbose=False):

        find = re.compile(pat)
        files = os.listdir(src_dir)

        for f in files:
            if os.path.isfile(f) and find.match(f):
                if verbose:
                    print(" * put %s" % f)

                self.put(os.path.join(src_dir, f), f)

    def get(self, src, dst=None):

        if src not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(src))

        if dst is None:
            dst = src

        f = open(dst, "wb")

        try:
            self.exec_("f = open('%s', 'rb')" % self.__fqn(src))
            ret = self.exec_(
                "while True:\r\n"
                "  c = ubinascii.hexlify(f.read(%s))\r\n"
                "  if not len(c):\r\n"
                "    break\r\n"
                "  sys.stdout.write(c)\r\n" % self.BIN_CHUNK_SIZE
            )
        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

        f.write(binascii.unhexlify(ret))
        f.close()

    def mget(self, dst_dir, pat, verbose=False):

        files = self.ls(add_dirs=False)
        find = re.compile(pat)

        for f in files:
            if find.match(f):
                if verbose:
                    print(" * get %s" % f)

                self.get(f, dst=os.path.join(dst_dir, f))

    def gets(self, src):

        if src not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self.__fqn(src))

        try:
            self.exec_("f = open('%s', 'r')" % self.__fqn(src))
            ret = self.exec_("for l in f: sys.stdout.write(l),")
        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

        if isinstance(ret, bytes):
            ret = ret.decode('utf-8')

        return ret

    def puts(self, dst, lines):

        try:

            self.exec_("f = open('%s', 'w')" % self.__fqn(dst))

            for l in lines:
                self.exec_("f.write('%s')" % l.encode("string-escape"))

            self.exec_("f.close()")

        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)

    def size(self, target):

        return len(self.gets(target))

    def cd(self, dir):

        if dir.startswith("/"):
            tmp_dir = dir
        elif dir == "..":
            tmp_dir, _ = os.path.split(self.dir)
        else:
            tmp_dir = self.__fqn(dir)

        # see if the new dir exists
        try:
            self.eval("os.listdir('%s')" % tmp_dir)
            self.dir = tmp_dir
        except PyboardError:
            raise RemoteIOError("Invalid directory: %s" % dir)

    def pwd(self):

        return self.dir

    def md(self, dir):

        if dir in self.ls():
            raise RemoteIOError("File or directory already exists: '%s'" % self.__fqn(dir))

        try:
            self.eval("os.mkdir('%s')" % self.__fqn(dir))
        except PyboardError as e:
            raise RemoteIOError("Device communication failed: %s" % e)
