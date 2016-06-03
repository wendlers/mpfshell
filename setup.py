#!/usr/bin/env python

from distutils.core import setup

setup(name='mpfshell',
      version='0.5',
      description='A simple shell based file explorer ESP8266 and WiPy Micropython devices.',
      author='Stefan Wendler',
      author_email='sw@kaltpost.de',
      url='https://www.kaltpost.de/',
      requires=['pyserial', 'colorama'],
      packages=['mp'],
      scripts=['mpfshell']
      )
