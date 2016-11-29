import pytest

from mp.tokenizer import Tokenizer, Token


class TestTokenizer:

    def __cmp_tokens(self, a, b):

        if len(a) != len(b):
            return False

        for i in range(len(a)):
            if a[i].kind != b[i].kind or a[i].value != b[i].value:
                return False

        return True

    def test_valid_strings(self):

        tests = [
            ('simple1', [
                Token(Token.STR, 'simple1')]),
            ('simple1 simple2.txt', [
                Token(Token.STR, 'simple1'),
                Token(Token.STR, 'simple2.txt')]),
            ('"Quoted"', [
                Token(Token.QSTR, 'Quoted')]),
            ('"Quoted with whitespace" non-quoted', [
                Token(Token.QSTR, 'Quoted with whitespace'),
                Token(Token.STR, 'non-quoted')]),
            ('"$1+2  _3%2*1+2-2/#.py~"  $1+2_3%2*1+2-2/#.py~', [
                Token(Token.QSTR, '$1+2  _3%2*1+2-2/#.py~'),
                Token(Token.STR, '$1+2_3%2*1+2-2/#.py~')]),
        ]

        t = Tokenizer()

        for string, exp_tokens in tests:
            tokens, rest = t.tokenize(string)
            assert rest == ''
            assert self.__cmp_tokens(exp_tokens, tokens)

    def test_invalid_strings(self):

        tests = [
            ('char ? is invalid', '? is invalid'),
            ('"char ? is invalid"', '"char ? is invalid"'),
            ('"unbalanced quotes', '"unbalanced quotes'),
            ('"valid quotes" valid "unbalanced quotes', '"unbalanced quotes'),
            ('unbalanced quotes"', '"'),
        ]

        t = Tokenizer()

        for string, exp_rest in tests:
            tokens, rest = t.tokenize(string)
            assert rest == exp_rest
