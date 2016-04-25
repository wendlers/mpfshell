#!/usr/bin/env python

from distutils.core import setup

setup(name='mpfshell',
      version='0.2',
      description='A simple shell based file explorer and FUSE based mounter for ESP8266 Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://www.kaltpost.de/',
      requires=['pyserial', 'fusepy', 'colorama'],
      packages=['mp'],
      scripts=['mpfshell', 'mpfmount']
      )
