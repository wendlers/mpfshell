#!/usr/bin/env python

from mp import version
from distutils.core import setup

setup(name='mpfshell',
      version=version.FULL,
      description='A simple shell based file explorer ESP8266 and WiPy Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://www.kaltpost.de/',
      install_requires=['pyserial', 'colorama', 'websocket_client'],
      packages=['mp'],
      scripts=['mpfshell'],
      )
