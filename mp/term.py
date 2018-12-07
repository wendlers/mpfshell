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


import serial

if serial.VERSION.startswith("2."):

    # see if we could use the legacy Miniterm implementation
    from serial.tools.miniterm import (
        Miniterm,
        console,
        CONVERT_CRLF,
        CONVERT_CR,
        CONVERT_LF,
        NEWLINE_CONVERISON_MAP,
    )

    class Term(Miniterm):
        def __init__(self, serial_instance, echo=False, eol="crlf"):

            self.serial = serial_instance

            convert = {"cr": CONVERT_CR, "lf": CONVERT_LF, "crlf": CONVERT_CRLF}

            self.console = console
            self.echo = echo
            self.repr_mode = 0
            self.convert_outgoing = convert[eol]
            self.newline = NEWLINE_CONVERISON_MAP[self.convert_outgoing]
            self.dtr_state = True
            self.rts_state = True
            self.break_state = False

            self.exit_character = None
            self.menu_character = None
            self.raw = None

            self.console.setup()

        def set_rx_encoding(self, enc):
            pass

        def set_tx_encoding(self, enc):
            pass


else:

    # see if we could use the new Miniterm implementation
    from serial.tools.miniterm import Miniterm

    Term = Miniterm
