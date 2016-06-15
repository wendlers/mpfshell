import os
import pytest

from mp.mpfexp import ConError
from mp.mpfexp import MpFileExplorer


class TestMpfexp:

    def __create_file(self, file, data = b""):

        with open(file, "wb") as f:
            f.write(data)

    def __create_dir(self, dir):

        os.mkdir(dir)

    def test_connect(self):

        fe = MpFileExplorer("ws:192.168.1.121,python")
        assert "esp8266" == fe.sysname

    def test_connect_fail_ip(self):

        with pytest.raises(ConError):
            MpFileExplorer("ws:192.168.2.121,python")

    def test_connect_fail_passwd(self):

        with pytest.raises(ConError):
            MpFileExplorer("ws:192.168.1.121,java")

    def test_put(self, tmpdir):

        print(tmpdir)
        self.__create_file(os.path.join(str(tmpdir), "file1"))
        self.__create_file(os.path.join(str(tmpdir), "file2"))

        self.__create_dir(os.path.join(str(tmpdir), "dir1"))
        self.__create_dir(os.path.join(str(tmpdir), "dir2"))

        os.chdir(str(tmpdir))

        # fe = MpFileExplorer("ws:192.168.1.111,python")
