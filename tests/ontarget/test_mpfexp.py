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
import pytest

from mp.mpfshell import RemoteIOError


@pytest.mark.usefixtures("mpsetup")
class TestMpfexp:
    """
    Tests for the MpFileExplorer class.
    """

    def __create_local_file(self, file, data =b""):

        with open(file, "wb") as f:
            f.write(data)

    def test_directory_handling(self, mpfexp):

        assert "/" == mpfexp.pwd()

        mpfexp.md('dir1')
        mpfexp.md('dir 1')
        mpfexp.md('dir1/subdir1')

        # no duplicate directory names
        with pytest.raises(RemoteIOError):
            mpfexp.md('dir1')

        with pytest.raises(RemoteIOError):
            mpfexp.md('dir1/subdir1')

        # no subdir in non existing dir
        with pytest.raises(RemoteIOError):
            mpfexp.md('dir2/subdir1')

        # relative directory creating
        mpfexp.cd('dir1')
        assert "/dir1" == mpfexp.pwd()
        mpfexp.md('subdir2')

        # created dirs visible for ls and marked as directory
        mpfexp.cd('/')
        assert "/" == mpfexp.pwd()
        assert ('dir1', 'D') in mpfexp.ls(True, True, True)
        assert ('dir 1', 'D') in mpfexp.ls(True, True, True)

        # no dir with same name as existing file
        with pytest.raises(RemoteIOError):
            mpfexp.md('boot.py')

        # subdirs are visible for ls
        mpfexp.cd('dir1')
        assert "/dir1" == mpfexp.pwd()
        assert [('subdir1', 'D'), ('subdir2', 'D')] == mpfexp.ls(True, True, True)

        mpfexp.cd('subdir1')
        assert "/dir1/subdir1" == mpfexp.pwd()
        assert [] == mpfexp.ls(True, True, True)

        mpfexp.cd('..')
        mpfexp.cd('subdir2')
        assert "/dir1/subdir2" == mpfexp.pwd()
        assert [] == mpfexp.ls(True, True, True)

        # no duplicate directory names
        with pytest.raises(RemoteIOError):
            mpfexp.cd('subdir1')

        #FIXME: not working as expected yet
        #mpfexp.cd('../subdir1')
        #assert "/dir1/subdir1" == mpfexp.pwd()

        # allow whitespaces in dir names
        mpfexp.cd('/dir 1')
        assert "/dir 1" == mpfexp.pwd()
        assert [] == mpfexp.ls(True, True, True)

    def test_file_handling(self, mpfexp, tmpdir):

        os.chdir(str(tmpdir))
        data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99"
        self.__create_local_file("file1", data)

        # upload with same name
        mpfexp.put("file1")

        # upload with different name
        mpfexp.put("file1", "file2")
        assert ('file1', 'F') in mpfexp.ls(True, True, True)
        assert ('file2', 'F') in mpfexp.ls(True, True, True)

        os.remove("file1")
        assert not os.path.isfile("file1")

        # download and compare
        mpfexp.get("file1")
        mpfexp.get("file2")
        mpfexp.get("file1", "file3")

        for name in ["file1", "file2", "file3"]:
            with open(name, "rb") as f:
                assert data == f.read()

        # overwrite existing file
        data = b"\xaa\xbb\xcc\xdd\xee\xff"
        self.__create_local_file("file1", data)

        mpfexp.put("file1")

        with open("file1", "rb") as f:
            assert data == f.read()

        # file with name of existing directory not allowed
        self.__create_local_file("dir2")

        mpfexp.md("dir2")

        with pytest.raises(RemoteIOError):
            mpfexp.put("file1", "dir2")

        with pytest.raises(RemoteIOError):
            mpfexp.put("dir2")

        # put files to subdir
        mpfexp.put("file1", "dir2/file1")
        mpfexp.cd("dir2")
        mpfexp.put("file2", "file2")
        assert [('file1', 'F'), ('file2', 'F')] == mpfexp.ls(True, True, True)
        mpfexp.cd("/")

        # fail to put to non-existing directory
        with pytest.raises(RemoteIOError):
            mpfexp.put("file1", "dir3/file1")

        # fail to get non-existing file
        with pytest.raises(RemoteIOError):
            mpfexp.get("file99")

        with pytest.raises(RemoteIOError):
            mpfexp.get("dir2")

        with pytest.raises(RemoteIOError):
            mpfexp.get("dir2/file99")

        # fail to get to non-existing dir
        with pytest.raises(IOError):
            mpfexp.get("file1", "dir/file")

        # fail to put non existing file
        with pytest.raises(IOError):
            mpfexp.put("file99")

        # allow whitespaces in file-names
        mpfexp.put("file1", "file 1")
        mpfexp.get("file 1")
        assert ('file 1', 'F') in mpfexp.ls(True, True, True)

    def test_removal(self, mpfexp, tmpdir):

        os.chdir(str(tmpdir))

        mpfexp.md("dir3")
        mpfexp.md("dir 3")
        self.__create_local_file("file10")

        mpfexp.put("file10")
        mpfexp.put("file10", "dir3/file1")
        mpfexp.put("file10", "dir3/file2")

        # don't allow deletion of non empty dirs
        with pytest.raises(RemoteIOError):
            mpfexp.rm("dir3")

        # delete files and empty dirs
        mpfexp.rm("file10")
        mpfexp.rm("dir3/file1")

        mpfexp.cd("dir3")
        mpfexp.rm("file2")
        assert [] == mpfexp.ls(True, True, True)

        mpfexp.cd("/")
        mpfexp.rm("dir3")
        mpfexp.rm("dir 3")

        assert ('file10', 'F') not in mpfexp.ls(True, True, True)
        assert ('dir3', 'D') not in mpfexp.ls(True, True, True)
        assert ('dir 3', 'D') not in mpfexp.ls(True, True, True)

        # fail to remove non-existing file or dir
        with pytest.raises(RemoteIOError):
            mpfexp.rm("file10")

        with pytest.raises(RemoteIOError):
            mpfexp.rm("dir3")

    def test_mputget(self, mpfexp, tmpdir):

        os.chdir(str(tmpdir))

        self.__create_local_file("file20")
        self.__create_local_file("file21")
        self.__create_local_file("file22")

        mpfexp.md("dir4")
        mpfexp.cd("dir4")
        mpfexp.mput(".", "file\.*")

        assert [("file20", "F"), ("file21", "F"), ("file22", "F")] == sorted(mpfexp.ls(True, True, True))

        os.mkdir("mget")
        os.chdir(os.path.join(str(tmpdir), "mget"))
        mpfexp.mget(".", "file\.*")
        assert ["file20", "file21", "file22"] == sorted(os.listdir("."))

        mpfexp.mget(".", "notmatching")

        with pytest.raises(RemoteIOError):
            mpfexp.mput(".", "*")

        with pytest.raises(RemoteIOError):
            mpfexp.mget(".", "*")

    def test_putsgets(self, mpfexp):

        mpfexp.md("dir5")
        mpfexp.cd("dir5")

        data = "Some random data"

        mpfexp.puts("file1", data)
        assert mpfexp.gets("file1").startswith(data)

        mpfexp.cd("/")

        with pytest.raises(RemoteIOError):
            mpfexp.puts("invalid/file1", "don't care")

        with pytest.raises(RemoteIOError):
            mpfexp.puts("dir5", "don't care")

        mpfexp.puts("dir5/file1", data)

        with pytest.raises(RemoteIOError):
            mpfexp.gets("dir5")

        with pytest.raises(RemoteIOError):
            mpfexp.gets("dir5/file99")

    def test_bigfile(self, mpfexp, tmpdir):

        os.chdir(str(tmpdir))

        data = b"\xab" * (1024 * 40)
        self.__create_local_file("file30", data)

        mpfexp.md("dir6")
        mpfexp.cd("dir6")
        mpfexp.put("file30", "file1")

        mpfexp.get("file1")

        with open("file1", "rb") as f:
            assert data == f.read()

    def test_stress(self, mpfexp, tmpdir):

        os.chdir(str(tmpdir))
        mpfexp.md("dir7")
        mpfexp.cd("dir7")

        for i in range(20):

            data = b"\xab" * (1024 * 1)
            self.__create_local_file("file40", data)

            mpfexp.put("file40", "file1")
            assert [("file1", "F")] == mpfexp.ls(True, True, True)

            mpfexp.put("file40", "file2")
            assert [("file1", "F"), ("file2", "F")] == mpfexp.ls(True, True, True)

            mpfexp.md("subdir1")
            assert [("subdir1", "D"), ("file1", "F"), ("file2", "F")] == mpfexp.ls(True, True, True)

            mpfexp.rm("file1")
            mpfexp.rm("file2")
            mpfexp.cd("subdir1")
            mpfexp.cd("..")
            mpfexp.rm("subdir1")

            assert [] == mpfexp.ls(True, True, True)
