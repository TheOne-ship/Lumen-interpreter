import unittest

from lumen import ast_nodes as ast
from lumen.errors import ParseError
from lumen.lexer import tokenize
from lumen.parser import parse


def p(source):
    return parse(tokenize(source))


class ParserTests(unittest.TestCase):
    def test_precedence_multiplication_before_addition(self):
        expr = p("1 + 2 * 3;")[0].expr
        self.assertIsInstance(expr, ast.Binary)
        self.assertEqual(expr.op, "+")
        self.assertEqual(expr.right.op, "*")

    def test_parentheses_override_precedence(self):
        expr = p("(1 + 2) * 3;")[0].expr
        self.assertEqual(expr.op, "*")
        self.assertEqual(expr.left.op, "+")

    def test_left_associative_subtraction(self):
        expr = p("10 - 4 - 3;")[0].expr
        self.assertEqual(expr.left.op, "-")      # (10 - 4) - 3

    def test_assignment_is_right_associative(self):
        expr = p("a = b = 5;")[0].expr
        self.assertIsInstance(expr, ast.Assign)
        self.assertIsInstance(expr.value, ast.Assign)

    def test_function_declaration(self):
        stmt = p("fn add(a, b) { return a + b; }")[0]
        self.assertIsInstance(stmt, ast.Let)
        self.assertEqual(stmt.value.params, ["a", "b"])

    def test_if_else(self):
        stmt = p("if (x) { y; } else { z; }")[0]
        self.assertIsInstance(stmt, ast.If)
        self.assertIsNotNone(stmt.else_branch)

    def test_index_assignment(self):
        expr = p("xs[0] = 1;")[0].expr
        self.assertIsInstance(expr, ast.IndexAssign)

    def test_missing_semicolon(self):
        with self.assertRaises(ParseError) as ctx:
            p("let x = 1\nlet y = 2;")
        self.assertIn("';'", str(ctx.exception))

    def test_invalid_assignment_target(self):
        with self.assertRaises(ParseError):
            p("1 + 2 = 3;")

    def test_unclosed_block(self):
        with self.assertRaises(ParseError):
            p("if (true) { print(1);")

    def test_duplicate_parameter(self):
        with self.assertRaises(ParseError):
            p("fn f(a, a) { }")


if __name__ == "__main__":
    unittest.main()
