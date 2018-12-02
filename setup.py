#!/usr/bin/env python
from setuptools import setup

from mp import version

setup(
    name="mpfshell",
    version=version.FULL,
    description="A simple shell based file explorer for ESP8266 and WiPy "
    "Micropython devices.",
    author="Stefan Wendler",
    author_email="sw@kaltpost.de",
    url="https://github.com/wendlers/mpfshell",
    download_url="https://github.com/wendlers/mpfshell/archive/0.8.1.tar.gz",
    install_requires=["pyserial", "colorama", "websocket_client"],
    packages=["mp"],
    keywords=["micropython", "shell", "file transfer", "development"],
    classifiers=[],
    entry_points={"console_scripts": ["mpfshell=mp.mpfshell:main"]},
)
