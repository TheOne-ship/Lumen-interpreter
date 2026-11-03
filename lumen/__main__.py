"""Command-line entry point.

    python -m lumen                 start the interactive REPL
    python -m lumen program.lm      run a source file
    python -m lumen --tokens file   show the tokens produced by the lexer
    python -m lumen --ast file      show the syntax tree produced by the parser
"""

import argparse
import pprint
import sys

from . import __version__
from .errors import LumenError
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import parse
from .values import to_str

BANNER = f"""Lumen {__version__} interactive shell
Type code and press Enter. Blocks can span multiple lines.
Commands: :help  :vars  :quit
"""

HELP = """Examples:
  let x = 5;
  fn square(n) { return n * n; }
  print(square(x));
  for (i in range(3)) { print(i); }
Built-ins: print input len str int float type range push pop join split sqrt abs clock"""


def run_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"Error: cannot open '{path}': {e.strerror}", file=sys.stderr)
        return 2
    try:
        Interpreter().run(source)
    except LumenError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def needs_more_input(text):
    """Keep reading lines while brackets are unbalanced (multi-line blocks)."""
    depth, in_string, escaped, in_comment = 0, False, False, False
    for ch in text:
        if in_comment:
            in_comment = ch != "\n"
        elif in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "#":
            in_comment = True
        elif ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
    return depth > 0 or in_string


def repl():
    interp = Interpreter()
    print(BANNER)
    while True:
        try:
            line = input("lumen> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return 0

        cmd = line.strip()
        if cmd in (":quit", ":q", "exit"):
            print("Bye!")
            return 0
        if cmd == ":help":
            print(HELP)
            continue
        if cmd == ":vars":
            user_vars = {k: v for k, v in interp.globals.values.items()
                         if not hasattr(v, "func")}
            for name, value in user_vars.items():
                print(f"  {name} = {to_str(value, True)}")
            if not user_vars:
                print("  (no variables yet)")
            continue

        source = line
        while needs_more_input(source):
            try:
                source += "\n" + input("  ...> ")
            except (EOFError, KeyboardInterrupt):
                print()
                source = ""
                break
        if not source.strip():
            continue

        try:
            result = interp.run(source)
            if result is not None:
                print(to_str(result, nested=True))
        except LumenError as e:
            print(e)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lumen", description="The Lumen language interpreter")
    ap.add_argument("file", nargs="?", help="source file to run (omit to start the REPL)")
    ap.add_argument("--tokens", action="store_true", help="print lexer tokens and exit")
    ap.add_argument("--ast", action="store_true", help="print the parsed AST and exit")
    ap.add_argument("--version", action="version", version=f"Lumen {__version__}")
    args = ap.parse_args(argv)

    if args.file is None:
        return repl()

    if args.tokens or args.ast:
        with open(args.file, encoding="utf-8") as f:
            source = f.read()
        try:
            tokens = tokenize(source)
            if args.tokens:
                for t in tokens:
                    print(f"{t.line:>4}  {t.type.name:<10} {t.lexeme}")
            else:
                for stmt in parse(tokens):
                    pprint.pprint(stmt, width=100)
        except LumenError as e:
            print(e, file=sys.stderr)
            return 1
        return 0

    return run_file(args.file)


if __name__ == "__main__":
    sys.exit(main())
