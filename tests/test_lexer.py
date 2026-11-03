import unittest

from lumen.errors import LexError
from lumen.lexer import tokenize
from lumen.tokens import T


def types(source):
    return [t.type for t in tokenize(source)]


class LexerTests(unittest.TestCase):
    def test_let_statement(self):
        self.assertEqual(types("let x = 10;"),
                         [T.LET, T.IDENT, T.ASSIGN, T.NUMBER, T.SEMICOLON, T.EOF])

    def test_two_character_operators(self):
        self.assertEqual(types("== != <= >= < > = !"),
                         [T.EQ, T.BANG_EQ, T.LE, T.GE, T.LT, T.GT, T.ASSIGN, T.BANG, T.EOF])

    def test_numbers(self):
        toks = tokenize("42 3.14")
        self.assertEqual(toks[0].value, 42)
        self.assertIsInstance(toks[0].value, int)
        self.assertEqual(toks[1].value, 3.14)

    def test_string_with_escapes(self):
        tok = tokenize(r'"a\tb\n\"q\""')[0]
        self.assertEqual(tok.value, 'a\tb\n"q"')

    def test_keywords_vs_identifiers(self):
        self.assertEqual(types("fn function let letter"),
                         [T.FN, T.IDENT, T.LET, T.IDENT, T.EOF])

    def test_comments_are_skipped(self):
        self.assertEqual(types("# a comment\nx # trailing"), [T.IDENT, T.EOF])

    def test_line_numbers(self):
        toks = tokenize("a\nb\n\nc")
        self.assertEqual([t.line for t in toks[:3]], [1, 2, 4])

    def test_unterminated_string(self):
        with self.assertRaises(LexError):
            tokenize('"oops')

    def test_unexpected_character(self):
        with self.assertRaises(LexError) as ctx:
            tokenize("let x = 5 @ 3;")
        self.assertIn("@", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
