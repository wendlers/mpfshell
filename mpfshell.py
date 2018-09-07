#!/usr/bin/env python

import sys

from mp.mpfshell import main

try:
    main()
except Exception as e:
    sys.stderr.write(str(e) + "\n")
    exit(1)
