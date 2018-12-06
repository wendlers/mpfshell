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


import ast
import binascii
import getpass
import logging
import os
import re
import sre_constants
import subprocess

from mp.conbase import ConError
from mp.conserial import ConSerial
from mp.contelnet import ConTelnet
from mp.conwebsock import ConWebsock
from mp.pyboard import Pyboard, PyboardError
from mp.retry import retry


def _was_file_not_existing(exception):
    """
    Helper function used to check for ENOENT (file doesn't exist),
    ENODEV (device doesn't exist, but handled in the same way) or
    EINVAL errors in an exception. Treat them all the same for the
    time being. TODO: improve and nuance.

    :param  exception:      exception to examine
    :return:                True if non-existing
    """

    stre = str(exception)
    return any(err in stre for err in ("ENOENT", "ENODEV", "EINVAL", "OSError:"))


class RemoteIOError(IOError):
    pass


class MpFileExplorer(Pyboard):

    BIN_CHUNK_SIZE = 64
    MAX_TRIES = 3

    def __init__(self, constr, reset=False):
        """
        Supports the following connection strings.

            ser:/dev/ttyUSB1,<baudrate>
            tn:192.168.1.101,<login>,<passwd>
            ws:192.168.1.102,<passwd>

        :param constr:      Connection string as defined above.
        """

        self.reset = reset

        try:
            Pyboard.__init__(self, self.__con_from_str(constr))
        except Exception as e:
            raise ConError(e)

        self.dir = None
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

            con = ConSerial(port=port, baudrate=baudrate, reset=self.reset)

        elif proto.strip(" ") == "tn":

            host = params[0].strip(" ")

            if len(params) > 1:
                login = params[1].strip(" ")
            else:
                print("")
                login = input("telnet login : ")

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

    def _fqn(self, name):
        return os.path.join(self.dir, name)

    def __set_sysname(self):
        self.sysname = self.eval("uos.uname()[0]").decode("utf-8")

    def close(self):

        Pyboard.close(self)
        self.dir = None

    def teardown(self):

        self.exit_raw_repl()
        self.sysname = None

    def setup(self):

        self.enter_raw_repl()
        self.exec_("import uos, sys")
        self.exec_(
            "try:\n    import ubinascii\nexcept ImportError:\n    import binascii as ubinascii"
        )

        # New version mounts files on /flash so lets set dir based on where we are in
        # filesystem.
        # Using the "path.join" to make sure we get "/" if "os.getcwd" returns "".
        self.dir = os.path.join("/", self.eval("uos.getcwd()").decode("utf8"))

        self.__set_sysname()

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def ls(self, add_files=True, add_dirs=True, add_details=False):

        files = []

        try:
            res = self.eval("list(uos.ilistdir('%s'))" % self.dir)
        except Exception as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("No such directory: %s" % self.dir)
            else:
                raise PyboardError(e)

        entries = ast.literal_eval(res.decode("utf-8"))

        if self.sysname == "WiPy" and self.dir == "/":
            # Assume everything in the root is a mountpoint and return them as dirs.
            if add_details:
                return [(entry[0], "D") for entry in entries]
            else:
                return [entry[0] for entry in entries]

        for entry in entries:
            fname, ftype, inode = entry[:3]
            fchar = "D" if ftype == 0x4000 else "F"
            if not ((fchar == "D" and add_dirs) or (fchar == "F" and add_files)):
                continue

            files.append((fname, fchar) if add_details else fname)

        if add_details:
            # Sort directories first, then filenames.
            return sorted(files, key=lambda x: (x[1], x[0]))
        else:
            return sorted(files)

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def rm(self, target):

        try:
            # 1st try to delete it as a file
            self.eval("uos.remove('%s')" % (self._fqn(target)))
        except PyboardError:
            try:
                # 2nd see if it is empty dir
                self.eval("uos.rmdir('%s')" % (self._fqn(target)))
            except PyboardError as e:
                # 3rd report error if nor successful
                if _was_file_not_existing(e):
                    if self.sysname == "WiPy":
                        raise RemoteIOError(
                            "No such file or directory or directory not empty: %s"
                            % target
                        )
                    else:
                        raise RemoteIOError("No such file or directory: %s" % target)
                elif "EACCES" in str(e):
                    raise RemoteIOError("Directory not empty: %s" % target)
                else:
                    raise e

    def mrm(self, pat, verbose=False):

        files = self.ls(add_dirs=False)
        find = re.compile(pat)

        for f in files:
            if find.match(f):
                if verbose:
                    print(" * rm %s" % f)

                self.rm(f)

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def put(self, src, dst=None):

        f = open(src, "rb")
        data = f.read()
        f.close()

        if dst is None:
            dst = src

        try:

            self.exec_("f = open('%s', 'wb')" % self._fqn(dst))

            while True:
                c = binascii.hexlify(data[: self.BIN_CHUNK_SIZE])
                if not len(c):
                    break

                self.exec_("f.write(ubinascii.unhexlify('%s'))" % c.decode("utf-8"))
                data = data[self.BIN_CHUNK_SIZE :]

            self.exec_("f.close()")

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("Failed to create file: %s" % dst)
            elif "EACCES" in str(e):
                raise RemoteIOError("Existing directory: %s" % dst)
            else:
                raise e

    def mput(self, src_dir, pat, verbose=False):

        try:

            find = re.compile(pat)
            files = os.listdir(src_dir)

            for f in files:
                if os.path.isfile(f) and find.match(f):
                    if verbose:
                        print(" * put %s" % f)

                    self.put(os.path.join(src_dir, f), f)

        except sre_constants.error as e:
            raise RemoteIOError("Error in regular expression: %s" % e)

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def get(self, src, dst=None):

        if src not in self.ls():
            raise RemoteIOError("No such file or directory: '%s'" % self._fqn(src))

        if dst is None:
            dst = src

        f = open(dst, "wb")

        try:

            self.exec_("f = open('%s', 'rb')" % self._fqn(src))
            ret = self.exec_(
                "while True:\r\n"
                "  c = ubinascii.hexlify(f.read(%s))\r\n"
                "  if not len(c):\r\n"
                "    break\r\n"
                "  sys.stdout.write(c)\r\n" % self.BIN_CHUNK_SIZE
            )

            self.exec_("f.close()")

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("Failed to read file: %s" % src)
            else:
                raise e

        f.write(binascii.unhexlify(ret))
        f.close()

    def mget(self, dst_dir, pat, verbose=False):

        try:

            files = self.ls(add_dirs=False)
            find = re.compile(pat)

            for f in files:
                if find.match(f):
                    if verbose:
                        print(" * get %s" % f)

                    self.get(f, dst=os.path.join(dst_dir, f))

        except sre_constants.error as e:
            raise RemoteIOError("Error in regular expression: %s" % e)

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def gets(self, src):

        try:

            self.exec_("f = open('%s', 'rb')" % self._fqn(src))
            ret = self.exec_(
                "while True:\r\n"
                "  c = ubinascii.hexlify(f.read(%s))\r\n"
                "  if not len(c):\r\n"
                "    break\r\n"
                "  sys.stdout.write(c)\r\n" % self.BIN_CHUNK_SIZE
            )

            self.exec_("f.close()")

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("Failed to read file: %s" % src)
            else:
                raise e

        try:

            return binascii.unhexlify(ret).decode("utf-8")

        except UnicodeDecodeError:

            s = ret.decode("utf-8")
            fs = "\nBinary file:\n\n"

            while len(s):
                fs += s[:64] + "\n"
                s = s[64:]

            return fs

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def puts(self, dst, lines):

        try:

            data = lines.encode("utf-8")

            self.exec_("f = open('%s', 'wb')" % self._fqn(dst))

            while True:
                c = binascii.hexlify(data[: self.BIN_CHUNK_SIZE])
                if not len(c):
                    break

                self.exec_("f.write(ubinascii.unhexlify('%s'))" % c.decode("utf-8"))
                data = data[self.BIN_CHUNK_SIZE :]

            self.exec_("f.close()")

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("Failed to create file: %s" % dst)
            elif "EACCES" in str(e):
                raise RemoteIOError("Existing directory: %s" % dst)
            else:
                raise e

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def cd(self, target):

        if target.startswith("/"):
            tmp_dir = target
        elif target == "..":
            tmp_dir, _ = os.path.split(self.dir)
        else:
            tmp_dir = self._fqn(target)

        # see if the new dir exists
        try:

            self.eval("uos.listdir('%s')" % tmp_dir)
            self.dir = tmp_dir

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("No such directory: %s" % target)
            else:
                raise e

    def pwd(self):
        return self.dir

    @retry(PyboardError, tries=MAX_TRIES, delay=1, backoff=2, logger=logging.root)
    def md(self, target):

        try:

            self.eval("uos.mkdir('%s')" % self._fqn(target))

        except PyboardError as e:
            if _was_file_not_existing(e):
                raise RemoteIOError("Invalid directory name: %s" % target)
            elif "EEXIST" in str(e):
                raise RemoteIOError("File or directory exists: %s" % target)
            else:
                raise e

    def mpy_cross(self, src, dst=None):

        if dst is None:
            return_code = subprocess.call("mpy-cross %s" % (src), shell=True)
        else:
            return_code = subprocess.call("mpy-cross -o %s %s" % (dst, src), shell=True)

        if return_code != 0:
            raise IOError("Filed to compile: %s" % src)


class MpFileExplorerCaching(MpFileExplorer):
    def __init__(self, constr, reset=False):
        MpFileExplorer.__init__(self, constr, reset)

        self.cache = {}

    def __cache(self, path, data):

        logging.debug("caching '%s': %s" % (path, data))
        self.cache[path] = data

    def __cache_hit(self, path):

        if path in self.cache:
            logging.debug("cache hit for '%s': %s" % (path, self.cache[path]))
            return self.cache[path]

        return None

    def ls(self, add_files=True, add_dirs=True, add_details=False):

        hit = self.__cache_hit(self.dir)

        if hit is None:
            hit = MpFileExplorer.ls(self, True, True, True)
            self.__cache(self.dir, hit)

        files = [f for f in hit if ((add_files and f[1] == "F") or (add_dirs and f[1] == "D"))]
        files.sort(key=lambda x: (x[1], x[0]))
        if not add_details:
            files = [f[0] for f in files]
        return files

    def put(self, src, dst=None):

        MpFileExplorer.put(self, src, dst)

        if dst is None:
            dst = src

        path = os.path.split(self._fqn(dst))
        newitm = path[-1]
        parent = path[:-1][0]

        hit = self.__cache_hit(parent)

        if hit is not None:
            if not (dst, "F") in hit:
                self.__cache(parent, hit + [(newitm, "F")])

    def puts(self, dst, lines):

        MpFileExplorer.puts(self, dst, lines)

        path = os.path.split(self._fqn(dst))
        newitm = path[-1]
        parent = path[:-1][0]

        hit = self.__cache_hit(parent)

        if hit is not None:
            if not (dst, "F") in hit:
                self.__cache(parent, hit + [(newitm, "F")])

    def md(self, dir):

        MpFileExplorer.md(self, dir)

        path = os.path.split(self._fqn(dir))
        newitm = path[-1]
        parent = path[:-1][0]

        hit = self.__cache_hit(parent)

        if hit is not None:
            if not (dir, "D") in hit:
                self.__cache(parent, hit + [(newitm, "D")])

    def rm(self, target):

        MpFileExplorer.rm(self, target)

        path = os.path.split(self._fqn(target))
        rmitm = path[-1]
        parent = path[:-1][0]

        hit = self.__cache_hit(parent)

        if hit is not None:
            files = []

            for f in hit:
                if f[0] != rmitm:
                    files.append(f)

            self.__cache(parent, files)
