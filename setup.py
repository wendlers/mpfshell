#!/usr/bin/env python

from distutils.core import setup

setup(name='mpfshell',
      version='0.1',
      description='A simple shell based file explorer and FUSE based mounter for ESP8266 Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://www.kaltpost.de/',
      packages=['mp'],
      scripts=['mpfshell', 'mpfmount']
      )
