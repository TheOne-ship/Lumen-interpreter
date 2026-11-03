"""Abstract Syntax Tree (AST) node definitions.

The parser builds a tree of these nodes; the interpreter walks the tree
to execute the program.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------- expressions
@dataclass
class Literal:
    value: object
    line: int = 0


@dataclass
class Variable:
    name: str
    line: int = 0


@dataclass
class Assign:
    name: str
    value: object
    line: int = 0


@dataclass
class Unary:
    op: str
    operand: object
    line: int = 0


@dataclass
class Binary:
    left: object
    op: str
    right: object
    line: int = 0


@dataclass
class Logical:
    left: object
    op: str            # "and" / "or"
    right: object
    line: int = 0


@dataclass
class Call:
    callee: object
    args: List[object]
    line: int = 0


@dataclass
class ListLiteral:
    items: List[object]
    line: int = 0


@dataclass
class Index:
    target: object
    index: object
    line: int = 0


@dataclass
class IndexAssign:
    target: object
    index: object
    value: object
    line: int = 0


@dataclass
class FunctionExpr:
    name: Optional[str]
    params: List[str]
    body: List[object]
    line: int = 0


# ----------------------------------------------------------------- statements
@dataclass
class ExprStmt:
    expr: object
    line: int = 0


@dataclass
class Let:
    name: str
    value: object
    line: int = 0


@dataclass
class Block:
    statements: List[object] = field(default_factory=list)
    line: int = 0


@dataclass
class If:
    condition: object
    then_branch: object
    else_branch: Optional[object]
    line: int = 0


@dataclass
class While:
    condition: object
    body: object
    line: int = 0


@dataclass
class For:
    var: str
    iterable: object
    body: object
    line: int = 0


@dataclass
class Return:
    value: Optional[object]
    line: int = 0


@dataclass
class Break:
    line: int = 0


@dataclass
class Continue:
    line: int = 0
