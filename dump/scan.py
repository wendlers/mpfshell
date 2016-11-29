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

        valid_fnchars = "A-Za-z0-9_%#~@\$!\*\.\+\-"

        tokens = [
            (r'[%s]+' % valid_fnchars, lambda scanner, token: Token(Token.STR, token)),
            (r'"[%s ]+"' % valid_fnchars, lambda scanner, token: Token(Token.QSTR, token[1:-1])),
            (r'[ ]', lambda scanner, token: None)
        ]

        self.scanner = re.Scanner(tokens)

    def tokenize(self, string):

        return self.scanner.scan(string)


t = Tokenizer()

r = t.tokenize('"a1+2 _3%2*1+2-2#.py"')
print(r)