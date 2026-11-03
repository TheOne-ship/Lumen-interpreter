"""Built-in functions available in every Lumen program."""

import math
import time

from .errors import LumenRuntimeError
from .values import BuiltinFunction, is_number, require_number, to_str, type_name


def _print(interp, args, line):
    interp.write(" ".join(to_str(a) for a in args))
    return None


def _input(interp, args, line):
    prompt = to_str(args[0]) if args else ""
    return interp.read(prompt)


def _len(interp, args, line):
    value = args[0]
    if not isinstance(value, (str, list)):
        raise LumenRuntimeError(f"len() expects a string or list, got {type_name(value)}", line)
    return len(value)


def _str(interp, args, line):
    return to_str(args[0])


def _int(interp, args, line):
    value = args[0]
    try:
        if isinstance(value, str):
            return int(float(value.strip())) if "." in value else int(value.strip())
        if is_number(value):
            return int(value)
    except ValueError:
        pass
    raise LumenRuntimeError(f"Cannot convert {to_str(value, True)} to int", line)


def _float(interp, args, line):
    value = args[0]
    try:
        if isinstance(value, str) or is_number(value):
            return float(value)
    except ValueError:
        pass
    raise LumenRuntimeError(f"Cannot convert {to_str(value, True)} to float", line)


def _type(interp, args, line):
    return type_name(args[0])


def _range(interp, args, line):
    for a in args:
        if not isinstance(a, int) or isinstance(a, bool):
            raise LumenRuntimeError("range() arguments must be integers", line)
    if len(args) == 3 and args[2] == 0:
        raise LumenRuntimeError("range() step cannot be zero", line)
    return list(range(*args))


def _push(interp, args, line):
    lst, item = args
    if not isinstance(lst, list):
        raise LumenRuntimeError("push() expects a list as first argument", line)
    lst.append(item)
    return lst


def _pop(interp, args, line):
    lst = args[0]
    if not isinstance(lst, list):
        raise LumenRuntimeError("pop() expects a list", line)
    if not lst:
        raise LumenRuntimeError("pop() from empty list", line)
    return lst.pop()


def _join(interp, args, line):
    lst, sep = args
    if not isinstance(lst, list) or not isinstance(sep, str):
        raise LumenRuntimeError("join() expects (list, string)", line)
    return sep.join(to_str(x) for x in lst)


def _split(interp, args, line):
    text = args[0]
    sep = args[1] if len(args) > 1 else None
    if not isinstance(text, str) or (sep is not None and not isinstance(sep, str)):
        raise LumenRuntimeError("split() expects (string, string?)", line)
    if sep == "":
        return list(text)
    return text.split(sep)


def _sqrt(interp, args, line):
    n = require_number(args[0], "sqrt() argument", line)
    if n < 0:
        raise LumenRuntimeError("sqrt() of a negative number", line)
    return math.sqrt(n)


def _abs(interp, args, line):
    return abs(require_number(args[0], "abs() argument", line))


def _clock(interp, args, line):
    return time.perf_counter()


BUILTINS = [
    BuiltinFunction("print", _print, 0, float("inf")),
    BuiltinFunction("input", _input, 0, 1),
    BuiltinFunction("len", _len, 1),
    BuiltinFunction("str", _str, 1),
    BuiltinFunction("int", _int, 1),
    BuiltinFunction("float", _float, 1),
    BuiltinFunction("type", _type, 1),
    BuiltinFunction("range", _range, 1, 3),
    BuiltinFunction("push", _push, 2),
    BuiltinFunction("pop", _pop, 1),
    BuiltinFunction("join", _join, 2),
    BuiltinFunction("split", _split, 1, 2),
    BuiltinFunction("sqrt", _sqrt, 1),
    BuiltinFunction("abs", _abs, 1),
    BuiltinFunction("clock", _clock, 0),
]
