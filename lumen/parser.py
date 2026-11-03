"""Recursive-descent parser: turns a token list into an AST.

Grammar (lowest to highest precedence):

    program     -> declaration* EOF
    declaration -> fnDecl | letDecl | statement
    fnDecl      -> "fn" IDENT "(" params? ")" block
    letDecl     -> "let" IDENT "=" expression ";"
    statement   -> ifStmt | whileStmt | forStmt | returnStmt
                 | "break" ";" | "continue" ";" | block | exprStmt
    ifStmt      -> "if" "(" expression ")" statement ( "else" statement )?
    whileStmt   -> "while" "(" expression ")" statement
    forStmt     -> "for" "(" IDENT "in" expression ")" statement
    returnStmt  -> "return" expression? ";"
    block       -> "{" declaration* "}"

    expression  -> assignment
    assignment  -> ( IDENT | call "[" expression "]" ) "=" assignment | or
    or          -> and ( "or" and )*
    and         -> equality ( "and" equality )*
    equality    -> comparison ( ( "==" | "!=" ) comparison )*
    comparison  -> term ( ( "<" | "<=" | ">" | ">=" ) term )*
    term        -> factor ( ( "+" | "-" ) factor )*
    factor      -> unary ( ( "*" | "/" | "%" ) unary )*
    unary       -> ( "-" | "!" | "not" ) unary | call
    call        -> primary ( "(" args? ")" | "[" expression "]" )*
    primary     -> NUMBER | STRING | "true" | "false" | "nil" | IDENT
                 | "(" expression ")" | "[" args? "]"
                 | "fn" "(" params? ")" block
"""

from . import ast_nodes as ast
from .errors import ParseError
from .tokens import T


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---- token helpers -------------------------------------------------
    def peek(self):
        return self.tokens[self.pos]

    def previous(self):
        return self.tokens[self.pos - 1]

    def check(self, *types):
        return self.peek().type in types

    def advance(self):
        if not self.check(T.EOF):
            self.pos += 1
        return self.previous()

    def match(self, *types):
        if self.check(*types):
            self.advance()
            return True
        return False

    def expect(self, type_, message):
        if self.check(type_):
            return self.advance()
        tok = self.peek()
        found = "end of input" if tok.type == T.EOF else f"'{tok.lexeme}'"
        raise ParseError(f"{message}, found {found}", tok.line)

    def end_statement(self):
        # Semicolons are required, except right before '}' or end of input
        # (this keeps the REPL friendly: `print(1 + 2)` works without ';').
        if self.match(T.SEMICOLON):
            return
        if self.check(T.RBRACE, T.EOF):
            return
        self.expect(T.SEMICOLON, "Expected ';' after statement")

    # ---- program / declarations ---------------------------------------
    def parse(self):
        statements = []
        while not self.check(T.EOF):
            statements.append(self.declaration())
        return statements

    def declaration(self):
        if self.check(T.FN) and self.tokens[self.pos + 1].type == T.IDENT:
            self.advance()
            return self.fn_declaration()
        if self.match(T.LET):
            return self.let_declaration()
        return self.statement()

    def fn_declaration(self):
        name_tok = self.expect(T.IDENT, "Expected function name")
        fn = self.function_rest(name_tok.lexeme, name_tok.line)
        return ast.Let(name_tok.lexeme, fn, name_tok.line)

    def function_rest(self, name, line):
        self.expect(T.LPAREN, "Expected '(' after function name")
        params = []
        if not self.check(T.RPAREN):
            while True:
                p = self.expect(T.IDENT, "Expected parameter name")
                if p.lexeme in params:
                    raise ParseError(f"Duplicate parameter '{p.lexeme}'", p.line)
                params.append(p.lexeme)
                if not self.match(T.COMMA):
                    break
        self.expect(T.RPAREN, "Expected ')' after parameters")
        self.expect(T.LBRACE, "Expected '{' before function body")
        body = self.block_body()
        return ast.FunctionExpr(name, params, body, line)

    def let_declaration(self):
        name = self.expect(T.IDENT, "Expected variable name after 'let'")
        self.expect(T.ASSIGN, "Expected '=' after variable name")
        value = self.expression()
        self.end_statement()
        return ast.Let(name.lexeme, value, name.line)

    # ---- statements ----------------------------------------------------
    def statement(self):
        if self.match(T.IF):
            return self.if_statement()
        if self.match(T.WHILE):
            return self.while_statement()
        if self.match(T.FOR):
            return self.for_statement()
        if self.match(T.RETURN):
            line = self.previous().line
            value = None
            if not self.check(T.SEMICOLON, T.RBRACE, T.EOF):
                value = self.expression()
            self.end_statement()
            return ast.Return(value, line)
        if self.match(T.BREAK):
            line = self.previous().line
            self.end_statement()
            return ast.Break(line)
        if self.match(T.CONTINUE):
            line = self.previous().line
            self.end_statement()
            return ast.Continue(line)
        if self.match(T.LBRACE):
            line = self.previous().line
            return ast.Block(self.block_body(), line)
        expr = self.expression()
        self.end_statement()
        return ast.ExprStmt(expr, getattr(expr, "line", 0))

    def block_body(self):
        statements = []
        while not self.check(T.RBRACE, T.EOF):
            statements.append(self.declaration())
        self.expect(T.RBRACE, "Expected '}' to close block")
        return statements

    def if_statement(self):
        line = self.previous().line
        self.expect(T.LPAREN, "Expected '(' after 'if'")
        cond = self.expression()
        self.expect(T.RPAREN, "Expected ')' after if condition")
        then_branch = self.statement()
        else_branch = self.statement() if self.match(T.ELSE) else None
        return ast.If(cond, then_branch, else_branch, line)

    def while_statement(self):
        line = self.previous().line
        self.expect(T.LPAREN, "Expected '(' after 'while'")
        cond = self.expression()
        self.expect(T.RPAREN, "Expected ')' after while condition")
        return ast.While(cond, self.statement(), line)

    def for_statement(self):
        line = self.previous().line
        self.expect(T.LPAREN, "Expected '(' after 'for'")
        var = self.expect(T.IDENT, "Expected loop variable name")
        self.expect(T.IN, "Expected 'in' after loop variable")
        iterable = self.expression()
        self.expect(T.RPAREN, "Expected ')' after for clause")
        return ast.For(var.lexeme, iterable, self.statement(), line)

    # ---- expressions ---------------------------------------------------
    def expression(self):
        return self.assignment()

    def assignment(self):
        expr = self.logic_or()
        if self.match(T.ASSIGN):
            eq = self.previous()
            value = self.assignment()           # right-associative
            if isinstance(expr, ast.Variable):
                return ast.Assign(expr.name, value, eq.line)
            if isinstance(expr, ast.Index):
                return ast.IndexAssign(expr.target, expr.index, value, eq.line)
            raise ParseError("Invalid assignment target", eq.line)
        return expr

    def logic_or(self):
        expr = self.logic_and()
        while self.match(T.OR):
            line = self.previous().line
            expr = ast.Logical(expr, "or", self.logic_and(), line)
        return expr

    def logic_and(self):
        expr = self.equality()
        while self.match(T.AND):
            line = self.previous().line
            expr = ast.Logical(expr, "and", self.equality(), line)
        return expr

    def _binary_level(self, next_level, *ops):
        expr = next_level()
        while self.match(*ops):
            op = self.previous()
            expr = ast.Binary(expr, op.lexeme, next_level(), op.line)
        return expr

    def equality(self):
        return self._binary_level(self.comparison, T.EQ, T.BANG_EQ)

    def comparison(self):
        return self._binary_level(self.term, T.LT, T.LE, T.GT, T.GE)

    def term(self):
        return self._binary_level(self.factor, T.PLUS, T.MINUS)

    def factor(self):
        return self._binary_level(self.unary, T.STAR, T.SLASH, T.PERCENT)

    def unary(self):
        if self.match(T.MINUS, T.BANG, T.NOT):
            op = self.previous()
            symbol = "-" if op.type == T.MINUS else "not"
            return ast.Unary(symbol, self.unary(), op.line)
        return self.call()

    def call(self):
        expr = self.primary()
        while True:
            if self.match(T.LPAREN):
                line = self.previous().line
                args = self.arguments(T.RPAREN, "Expected ')' after arguments")
                expr = ast.Call(expr, args, line)
            elif self.match(T.LBRACKET):
                line = self.previous().line
                index = self.expression()
                self.expect(T.RBRACKET, "Expected ']' after index")
                expr = ast.Index(expr, index, line)
            else:
                return expr

    def arguments(self, closer, message):
        args = []
        if not self.check(closer):
            while True:
                args.append(self.expression())
                if not self.match(T.COMMA):
                    break
        self.expect(closer, message)
        return args

    def primary(self):
        tok = self.peek()
        if self.match(T.NUMBER, T.STRING):
            return ast.Literal(tok.value, tok.line)
        if self.match(T.TRUE):
            return ast.Literal(True, tok.line)
        if self.match(T.FALSE):
            return ast.Literal(False, tok.line)
        if self.match(T.NIL):
            return ast.Literal(None, tok.line)
        if self.match(T.IDENT):
            return ast.Variable(tok.lexeme, tok.line)
        if self.match(T.LPAREN):
            expr = self.expression()
            self.expect(T.RPAREN, "Expected ')' after expression")
            return expr
        if self.match(T.LBRACKET):
            items = self.arguments(T.RBRACKET, "Expected ']' after list items")
            return ast.ListLiteral(items, tok.line)
        if self.match(T.FN):
            return self.function_rest(None, tok.line)

        found = "end of input" if tok.type == T.EOF else f"'{tok.lexeme}'"
        raise ParseError(f"Expected an expression, found {found}", tok.line)


def parse(tokens):
    return Parser(tokens).parse()
