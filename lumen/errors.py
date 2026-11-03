"""Error types raised by the Lumen interpreter.

Every error carries the line number where it happened so the user
gets a helpful message such as:  [line 4] RuntimeError: Undefined variable 'x'
"""


class LumenError(Exception):
    kind = "Error"

    def __init__(self, message, line=None):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self):
        where = f"[line {self.line}] " if self.line is not None else ""
        return f"{where}{self.kind}: {self.message}"


class LexError(LumenError):
    kind = "SyntaxError"


class ParseError(LumenError):
    kind = "SyntaxError"


class LumenRuntimeError(LumenError):
    kind = "RuntimeError"
