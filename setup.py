#!/usr/bin/env python

from mp import version
from distutils.core import setup

setup(name='mpfshell',
      version=version.FULL,
      description='A simple shell based file explorer for ESP8266 and WiPy Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://github.com/wendlers/mpfshell',
      download_url='https://github.com/wendlers/mpfshell/archive/0.8.1.tar.gz',
      install_requires=['pyserial', 'colorama', 'websocket_client'],
      packages=['mp'],
      scripts=['mpfshell'],
      keywords=['micropython', 'shell', 'file transfer', 'development'],
      classifiers=[],
)
