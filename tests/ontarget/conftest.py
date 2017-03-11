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

import pytest
import subprocess
import time

from mp.mpfexp import MpFileExplorer, MpFileExplorerCaching

_mpfexp_inst = None


def pytest_addoption(parser):
    """
    Add some custom parameters.

    :param parser:      Parser object
    """

    parser.addoption("--testcon", action="store", default="ser:/dev/ttyUSB0",
                     help="Connection string to use for tests")

    parser.addoption("--caching", action="store_true", default=False,
                     help="Enable caching of MpFileExplorer")

    parser.addoption("--nosetup", action="store_true", default=False,
                     help="Skip initial board setup")


@pytest.fixture(scope="module")
def mpsetup(request):
    """
    Initial setup. Mainly clear out everything from FS except "boot.py" and "port_config.py"

    :param request:     Request object
    """

    if not request.config.getoption("--nosetup"):

        fe = MpFileExplorer(request.config.getoption("--testcon"))
        fe.puts("pytest.py", """
def rm(path):
    import os
    files = os.listdir(path)
    for f in files:
        if f not in ['boot.py', 'port_config.py']:
            try:
                os.remove(path + '/' +  f)
            except:
                try:
                    os.rmdir(path + '/' +  f)
                except:
                    rm(path + '/' + f)
""")

        fe.exec_("import pytest")
        fe.exec_("pytest.rm(os.getcwd())")


@pytest.fixture(scope="function")
def mpfexp(request):
    """
    Fixture providing connected mMpFileExplorer instance

    :param request:     Request object
    :return:            MpFileExplorer instance
    """

    global _mpfexp_inst

    def teardown():
        _mpfexp_inst.close()

    if request.config.getoption("--caching"):
        _mpfexp_inst = MpFileExplorerCaching(request.config.getoption("--testcon"))
    else:
        _mpfexp_inst = MpFileExplorer(request.config.getoption("--testcon"))

    request.addfinalizer(teardown)

    return _mpfexp_inst

# enable logging of modules under test
import logging
logging.basicConfig(format='%(asctime)s\t%(levelname)s\t%(message)s',
                    filename='test.log', level=logging.DEBUG)
