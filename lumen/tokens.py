"""Token definitions for the Lumen language."""

from dataclasses import dataclass
from enum import Enum, auto


class T(Enum):
    # Single / double character symbols
    LPAREN = auto(); RPAREN = auto()
    LBRACE = auto(); RBRACE = auto()
    LBRACKET = auto(); RBRACKET = auto()
    COMMA = auto(); SEMICOLON = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    BANG = auto(); BANG_EQ = auto()
    ASSIGN = auto(); EQ = auto()
    LT = auto(); LE = auto(); GT = auto(); GE = auto()

    # Literals
    IDENT = auto(); NUMBER = auto(); STRING = auto()

    # Keywords
    LET = auto(); FN = auto(); RETURN = auto()
    IF = auto(); ELSE = auto(); WHILE = auto(); FOR = auto(); IN = auto()
    BREAK = auto(); CONTINUE = auto()
    TRUE = auto(); FALSE = auto(); NIL = auto()
    AND = auto(); OR = auto(); NOT = auto()

    EOF = auto()


KEYWORDS = {
    "let": T.LET, "fn": T.FN, "return": T.RETURN,
    "if": T.IF, "else": T.ELSE, "while": T.WHILE,
    "for": T.FOR, "in": T.IN,
    "break": T.BREAK, "continue": T.CONTINUE,
    "true": T.TRUE, "false": T.FALSE, "nil": T.NIL,
    "and": T.AND, "or": T.OR, "not": T.NOT,
}


@dataclass
class Token:
    type: T
    lexeme: str
    value: object
    line: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.lexeme!r}, line={self.line})"
