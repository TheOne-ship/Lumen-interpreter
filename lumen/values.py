"""Runtime values and helpers shared by the interpreter and built-ins."""

from .errors import LumenRuntimeError


class LumenFunction:
    """A user-defined function together with the scope it was created in."""

    def __init__(self, decl, closure):
        self.decl = decl
        self.closure = closure

    @property
    def name(self):
        return self.decl.name or "<anonymous>"

    @property
    def arity(self):
        return len(self.decl.params)

    def __repr__(self):
        return f"<fn {self.name}>"


class BuiltinFunction:
    """A function implemented in Python, e.g. print or len."""

    def __init__(self, name, func, min_args, max_args=None):
        self.name = name
        self.func = func
        self.min_args = min_args
        self.max_args = min_args if max_args is None else max_args

    def __repr__(self):
        return f"<builtin {self.name}>"


def type_name(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, (LumenFunction, BuiltinFunction)):
        return "function"
    return "unknown"


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_truthy(value):
    """false, nil, 0, "" and [] are falsy; everything else is truthy."""
    if value is None or value is False:
        return False
    if is_number(value):
        return value != 0
    if isinstance(value, (str, list)):
        return len(value) > 0
    return True


def values_equal(a, b):
    # Avoid Python's True == 1 quirk: values of different kinds are unequal.
    if is_number(a) and is_number(b):
        return a == b
    if type_name(a) != type_name(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a == b


def to_str(value, nested=False):
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e16:
            return f"{value:.1f}"
        return repr(value)
    if isinstance(value, str):
        return f'"{value}"' if nested else value
    if isinstance(value, list):
        return "[" + ", ".join(to_str(v, nested=True) for v in value) + "]"
    return repr(value)


def require_number(value, what, line):
    if not is_number(value):
        raise LumenRuntimeError(
            f"{what} must be a number, got {type_name(value)}", line)
    return value
