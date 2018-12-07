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

import re


class Token(object):

    STR = "STR"
    QSTR = "QSTR"

    def __init__(self, kind, value=None):

        self._kind = kind
        self._value = value

    @property
    def kind(self):
        return self._kind

    @property
    def value(self):
        return self._value

    def __repr__(self):

        if isinstance(self.value, str):
            v = "'%s'" % self.value
        else:
            v = str(self.value)

        return "Token('%s', %s)" % (self.kind, v)


class Tokenizer(object):
    def __init__(self):

        valid_fnchars = r"A-Za-z0-9_%#~@/\$!\*\.\+\-"

        tokens = [
            (r"[%s]+" % valid_fnchars, lambda scanner, token: Token(Token.STR, token)),
            (
                r'"[%s ]+"' % valid_fnchars,
                lambda scanner, token: Token(Token.QSTR, token[1:-1]),
            ),
            (r"[ ]", lambda scanner, token: None),
        ]

        self.scanner = re.Scanner(tokens)

    def tokenize(self, string):

        return self.scanner.scan(string)
