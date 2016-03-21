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

FUSE binding for Micropython.

For usage details see the README.md
"""

import time
import copy

import optparse as par

from errno import ENOENT, EIO
from stat import S_IFDIR, S_IFREG
from fuse import FUSE, FuseOSError, Operations

from mp.mpfexp import MpFileExplorer


class MpFileEntry(object):

    def __init__(self, mp, path, dirty=False, deleted=False, content=None):

        self.mp = mp

        self._path = path
        self._dirty = dirty
        self._deleted = deleted
        self._content = content

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def content(self):

        if self._content is None:
            self._content = self.mp.gets(self._path)

        return self._content

    @content.setter
    def content(self, value):
        self._content = value
        self._dirty = True

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value

    @property
    def deleted(self):
        return self._deleted

    @deleted.setter
    def deleted(self, value):
        self._deleted = value
        self._dirty = True

    @property
    def size(self):
        return len(self.content)

    def __str__(self):
        return "MpFileEntry(path=%s, dirty=%s, deleted=%s)" % (self._path, self._dirty, self._deleted)


class MpFuse(Operations):

    def __init__(self, mp, gid=0, uid=0):

        self.gid = gid
        self.uid = uid
        self.fh = 0
        self.ft = time.time()

        self.mp = mp
        self.cache = {}

        for f in self.mp.ls():
            self.cache[f] = MpFileEntry(self.mp, f)

    def getattr(self, path, fh=None):

        if path == '/':

            return dict(st_mode=(S_IFDIR | 0o777), st_mtime=self.ft, st_atime=self.ft, st_ctime=self.ft,
                        st_uid=self.uid, st_gid=self.gid)

        elif path == '/.commit':

            return dict(st_mode=(S_IFREG | 0o222), st_mtime=self.ft, st_atime=self.ft, st_ctime=self.ft,
                        st_uid=self.uid, st_gid=self.gid, st_size=0)

        else:
            try:
                p = path[1:].encode("ascii")
                s = self.cache[p].size

                return dict(st_mode=(S_IFREG | 0o666), st_mtime=self.ft, st_atime=self.ft, st_ctime=self.ft,
                            st_uid=self.uid, st_gid=self.gid, st_size=s)
            except:
                raise FuseOSError(ENOENT)

    def readdir(self, path, fh):

        if path == '/':

            for f in self.cache.values():
                if not f.deleted:
                    yield f.path

            yield ".commit"

    def open(self, path, flags):

        self.fh += 1
        return self.fh

    def create(self, path, mode, fi=None):

        if '/' in path[1:]:
            return -1

        p = path[1:].encode("ascii")
        self.cache[p] = MpFileEntry(self.mp, p, content="", dirty=True)

        self.fh += 1
        return self.fh

    def read(self, path, length, offset, fh):

        try:

            p = path[1:].encode("ascii")
            d = self.cache[p].content[offset:offset + length]
            return ''.join(d)

        except Exception as e:
            raise FuseOSError(EIO)

    def write(self, path, buf, offset, fh):

        try:
            if path == "/.commit":

                p = buf.strip(' ').strip('\n').strip('\r')

                if p == "*":
                    files = self.cache.keys()
                elif p in self.cache:
                    files = [p]
                else:
                    files = []

                for p in files:

                    print("commit checking: %s" % self.cache[p])

                    if self.cache[p].deleted:

                        print("-> deleting: %s" % p)
                        self.mp.rm(p)
                        del self.cache[p]

                    elif self.cache[p].dirty:

                        print("-> updating: %s" % p)
                        self.mp.puts(p, self.cache[p].content)
                        self.cache[p].dirty = False

            else:
                p = path[1:].encode("ascii")
                self.cache[p].content = self.cache[p].content[:offset] + buf
        except:
            raise FuseOSError(EIO)

        return len(buf)

    def unlink(self, path):

        p = path[1:].encode("ascii")
        self.cache[p].deleted = True

    def rename(self, old, new):

        if '/' in new[1:]:
            raise FuseOSError(EIO)

        try:

            po = old[1:].encode("ascii")
            pn = new[1:].encode("ascii")

            self.cache[pn] = copy.copy(self.cache[po])
            self.cache[pn].dirty = True
            self.cache[pn].path = pn

            self.cache[po].deleted = True

        except Exception as e:
            raise FuseOSError(EIO)

    def truncate(self, path, length, fh=None):

        if path == "/.commit":
            return

        try:

            p = path[1:].encode("ascii")
            self.cache[p].content = self.cache[p].content[0:length]

        except Exception as e:
            raise FuseOSError(EIO)


if __name__ == '__main__':

    usage = '%prog [options]'

    parser = par.OptionParser(usage)

    parser.add_option('-u', '--uid', default=0, type=int, help='UID to use for files (default 0)')
    parser.add_option('-g', '--gid', default=0, type=int, help='GID to use for files (default 1)')
    parser.add_option('-p', '--port', help='MP port')
    parser.add_option('-b', '--baudrate', default=115200, type=int, help='MP baudrate (default 115200)')
    parser.add_option('-m', '--mount', help='Mount point')

    (options, args) = parser.parse_args()

    if options.port is None:
        print('Port needs to be given!')
        exit(1)

    if options.mount is None:
        print('Mount point needs to be given!')
        exit(1)

    print("Mounting mpfs from device on port %s to %s" % (options.port, options.mount))
    print("Press CTRL+C to quit")

    FUSE(MpFuse(MpFileExplorer(device=options.port), options.uid, options.gid), options.mount, foreground=True)
