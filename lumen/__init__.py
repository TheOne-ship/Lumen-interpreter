"""Lumen: a small, dynamically typed programming language written in Python."""

from .errors import LexError, LumenError, LumenRuntimeError, ParseError
from .interpreter import Interpreter

__version__ = "1.0.0"
__all__ = ["Interpreter", "LumenError", "LexError", "ParseError", "LumenRuntimeError"]
