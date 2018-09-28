#!/usr/bin/env python

from mp import version
from distutils.core import setup

setup(name='mpfshell',
      version=version.FULL,
      description='A simple shell based file explorer for ESP8266 Or ESP32 and WiPy Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://github.com/junhuanchen/mpfshell',
      download_url='https://codeload.github.com/junhuanchen/mpfshell/zip/master',
      install_requires=['pyserial', 'colorama', 'websocket_client'],
      packages=['mp'],
      scripts=['mpfshell'],
      keywords=['micropython', 'shell', 'file transfer', 'development'],
      classifiers=[],
)
