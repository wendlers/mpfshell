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


class FileObject(object):

    def __init__(self, path, dirty=False, deleted=False, content=None):

        self._path = path
        self._dirty = dirty
        self._deleted = deleted
        self._content = content
        self._ft = time.time()
        self._mode = 0o666
        self._uid = 0
        self._gid = 0

    def _set_ft(self, ft=None):

        if ft is None:
            ft = time.time()

        self._ft = ft

    def on_read(self, offset, length):
        self._set_ft()
        return self.content[offset:offset + length]

    def on_write(self, offset, data):
        pass

    def on_truncate(self, length):
        pass

    def on_unlink(self):
        pass

    def on_getattr(self):

        return dict(st_mode=(S_IFREG | self.mode), st_mtime=self.ft, st_atime=self.ft, st_ctime=self.ft,
                    st_uid=self.uid, st_gid=self.gid, st_size=self.size)

    def on_rename(self, new):
        self._set_ft()

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def content(self):
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

    @property
    def ft(self):
        return self._ft

    @ft.setter
    def ft(self, value):
        self._ft = value

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, value):
        self._uid = value

    @property
    def gid(self):
        return self._gid

    @gid.setter
    def gid(self, value):
        self._gid = value

    def __str__(self):
        return "%s(path='%s', dirty=%s, deleted=%s, mode=%o)" % (self.__class__, self._path, self._dirty,
                                                                 self._deleted, self._mode)


class MpFileObject(FileObject):

    def __init__(self, mp, mp_files, path, dirty=False, deleted=False, content=None):
        FileObject.__init__(self, path, dirty, deleted, content)

        self._mp = mp
        self._mp_files = mp_files

    def on_write(self, offset, data):
        self._set_ft()
        self.content = self.content[:offset] + data

    def on_truncate(self, length):
        self._set_ft()
        self.content = self.content[0:length]

    def on_unlink(self):
        self._set_ft()
        self.deleted = True

    def on_rename(self, new):

        self._set_ft()

        self._mp_files[new] = copy.copy(self)
        self._mp_files[new].dirty = True
        self._mp_files[new].path = new

        self.deleted = True

    @property
    def content(self):

        if self._content is None:
            self._content = self._mp.gets(self._path)

        return self._content

    @content.setter
    def content(self, value):
        self._content = value
        self._dirty = True


class RootFileObject(FileObject):

    def __init__(self):
        FileObject.__init__(self, "", False, False, "")

        self._mode = 0o777

    def on_getattr(self):

        return dict(st_mode=(S_IFDIR | self.mode), st_mtime=self.ft, st_atime=self.ft, st_ctime=self.ft,
                    st_uid=self.uid, st_gid=self.gid)


class CommitFileObject(FileObject):

    def __init__(self, mp, mp_files):
        FileObject.__init__(self, ".commit", False, False, "")

        self._mode = 0o777
        self._mp = mp
        self._mp_files = mp_files
        self._content = "#!/bin/bash\n" \
                        "echo \"*\" > .commit\n"

    def on_write(self, offset, data):

        # TODO do not try to commit when serial port is released

        p = data.strip(' ').strip('\n').strip('\r')

        if p == "*":
            files = self._mp_files.keys()
        elif p in self._mp_files:
            files = [p]
        else:
            files = []

        for p in files:

            if not isinstance(self._mp_files[p], MpFileObject):
                continue

            if self._mp_files[p].deleted:

                self._mp.rm(p)
                del self._mp_files[p]

            elif self._mp_files[p].dirty:

                self._mp.puts(p, self._mp_files[p].content)
                self._mp_files[p].dirty = False


class ReleaseFileObject(FileObject):

    def __init__(self, mp):
        FileObject.__init__(self, ".release", False, False, "")

        self._mode = 0o222
        self._mp = mp

    def on_write(self, offset, data):

        p = data.strip(' ').strip('\n').strip('\r')

        if p == "1":
            self._mp.teardown()
            self._mp.close()
        else:
            self._mp.open()
            self._mp.setup()


class TerminalFileObject(FileObject):

    def __init__(self, mp):
        FileObject.__init__(self, ".terminal", False, False, "")

        self._mode = 0o777
        self._mp = mp
        self._content = "#!/bin/bash\n" \
                        "echo \"1\" > .release\n" \
                        "miniterm.py -p %s -b %d\n" \
                        "echo \"0\" > .release\n" % (self._mp.port, self._mp.baudrate)


class MpFuse(Operations):

    def __init__(self, mp, gid=0, uid=0):

        self.gid = gid
        self.uid = uid
        self.fh = 0
        self.ft = time.time()

        self.mp = mp
        self.cache = {"": RootFileObject()}

        for f in self.mp.ls():
            self.cache[f] = MpFileObject(self.mp, self.cache, f)

        self.cache[".commit"] = CommitFileObject(self.mp, self.cache)
        self.cache[".release"] = ReleaseFileObject(self.mp)
        self.cache[".terminal"] = TerminalFileObject(self.mp)

    def getattr(self, path, fh=None):

        try:
            o = self.cache[path[1:].encode("ascii")]
            return o.on_getattr()
        except:
            raise FuseOSError(ENOENT)

    def readdir(self, path, fh):

        # this is a flat filesystem
        if path == '/':
            for f in self.cache.values():
                if not isinstance(f, RootFileObject) and not f.deleted:
                    yield f.path

    def open(self, path, flags):

        self.fh += 1
        return self.fh

    def create(self, path, mode, fi=None):

        if '/' in path[1:]:
            return -1

        p = path[1:].encode("ascii")
        self.cache[p] = MpFileObject(self.mp, self.cache, p, content="", dirty=True)

        self.fh += 1
        return self.fh

    def read(self, path, length, offset, fh):

        try:
            o = self.cache[path[1:].encode("ascii")]
            return o.on_read(offset, length)
        except:
            raise FuseOSError(EIO)

    def write(self, path, buf, offset, fh):

        try:
            o = self.cache[path[1:].encode("ascii")]
            o.on_write(offset, buf)
        except:
            raise FuseOSError(EIO)

        return len(buf)

    def unlink(self, path):

        try:
            o = self.cache[path[1:].encode("ascii")]
            return o.on_unlink()
        except:
            raise FuseOSError(EIO)

    def rename(self, old, new):

        # this is a flat filesystem
        if '/' in new[1:]:
            raise FuseOSError(EIO)

        try:
            o = self.cache[old[1:].encode("ascii")]
            o.on_rename(new[1:].encode("ascii"))
        except Exception as e:
            raise FuseOSError(EIO)

    def truncate(self, path, length, fh=None):

        try:
            o = self.cache[path[1:].encode("ascii")]
            o.on_truncate(length)
        except:
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

    FUSE(MpFuse(MpFileExplorer(port=options.port), options.uid, options.gid), options.mount, foreground=True)
