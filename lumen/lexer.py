"""Lexer (tokenizer): turns Lumen source text into a list of tokens.

Example:
    let x = 10 + 2;
becomes
    LET  IDENT(x)  ASSIGN  NUMBER(10)  PLUS  NUMBER(2)  SEMICOLON  EOF
"""

from .errors import LexError
from .tokens import KEYWORDS, T, Token

SINGLE_CHAR = {
    "(": T.LPAREN, ")": T.RPAREN,
    "{": T.LBRACE, "}": T.RBRACE,
    "[": T.LBRACKET, "]": T.RBRACKET,
    ",": T.COMMA, ";": T.SEMICOLON,
    "+": T.PLUS, "-": T.MINUS, "*": T.STAR, "/": T.SLASH, "%": T.PERCENT,
}

# Characters that may be followed by '=' to form a two-character operator.
WITH_EQUALS = {
    "!": (T.BANG, T.BANG_EQ),
    "=": (T.ASSIGN, T.EQ),
    "<": (T.LT, T.LE),
    ">": (T.GT, T.GE),
}

ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


class Lexer:
    def __init__(self, source):
        self.src = source
        self.tokens = []
        self.start = 0      # start of the current lexeme
        self.pos = 0        # current character
        self.line = 1

    # ---- helpers -------------------------------------------------------
    def at_end(self):
        return self.pos >= len(self.src)

    def advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        return ch

    def peek(self, offset=0):
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else "\0"

    def add(self, type_, value=None):
        lexeme = self.src[self.start:self.pos]
        self.tokens.append(Token(type_, lexeme, value, self.line))

    # ---- main loop -----------------------------------------------------
    def tokenize(self):
        while not self.at_end():
            self.start = self.pos
            self.scan_token()
        self.tokens.append(Token(T.EOF, "", None, self.line))
        return self.tokens

    def scan_token(self):
        ch = self.advance()

        if ch in " \r\t":
            return
        if ch == "\n":
            self.line += 1
            return
        if ch == "#":                       # comment until end of line
            while self.peek() != "\n" and not self.at_end():
                self.advance()
            return
        if ch in SINGLE_CHAR:
            self.add(SINGLE_CHAR[ch])
            return
        if ch in WITH_EQUALS:
            single, double = WITH_EQUALS[ch]
            if self.peek() == "=":
                self.advance()
                self.add(double)
            else:
                self.add(single)
            return
        if ch == '"':
            self.string()
            return
        if ch.isdigit():
            self.number()
            return
        if ch.isalpha() or ch == "_":
            self.identifier()
            return

        raise LexError(f"Unexpected character '{ch}'", self.line)

    def string(self):
        start_line = self.line
        chars = []
        while self.peek() != '"':
            if self.at_end():
                raise LexError("Unterminated string", start_line)
            ch = self.advance()
            if ch == "\n":
                self.line += 1
            if ch == "\\":
                esc = self.advance() if not self.at_end() else ""
                if esc not in ESCAPES:
                    raise LexError(f"Unknown escape sequence '\\{esc}'", self.line)
                ch = ESCAPES[esc]
            chars.append(ch)
        self.advance()                      # closing quote
        self.add(T.STRING, "".join(chars))

    def number(self):
        while self.peek().isdigit():
            self.advance()
        is_float = False
        if self.peek() == "." and self.peek(1).isdigit():
            is_float = True
            self.advance()
            while self.peek().isdigit():
                self.advance()
        text = self.src[self.start:self.pos]
        self.add(T.NUMBER, float(text) if is_float else int(text))

    def identifier(self):
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()
        text = self.src[self.start:self.pos]
        self.add(KEYWORDS.get(text, T.IDENT))


def tokenize(source):
    return Lexer(source).tokenize()
