#!/usr/bin/env python

import sys

from mp.mpfshell import main

def view_all_serial():
    import serial.tools.list_ports
    print("Looking for computer port...")
    plist = list(serial.tools.list_ports.comports())

    if len(plist) <= 0:
        print("Serial Not Found!")
    else:
        for serial in plist:
            print("Serial Name :", serial[0])
    print("you can input 'open ", serial[0], "' and enter connect your BPI:bit.")

try:
    view_all_serial()
    main()
except Exception as e:
    sys.stderr.write(str(e) + "\n")
    exit(1)
