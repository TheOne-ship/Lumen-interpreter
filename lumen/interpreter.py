"""Tree-walking interpreter: executes the AST produced by the parser."""

import sys
import time

from . import ast_nodes as ast
from .builtins import BUILTINS
from .environment import Environment
from .errors import LumenRuntimeError
from .lexer import tokenize
from .parser import parse
from .values import (BuiltinFunction, LumenFunction, is_number, is_truthy,
                     require_number, to_str, type_name, values_equal)

MAX_CALL_DEPTH = 1000


# Control flow is implemented with Python exceptions that unwind the
# interpreter's own call stack back to the loop / function that handles them.
class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self, write=None, read=None, time_limit=None):
        """time_limit: maximum seconds a run may take (None = no limit).
        The web playground sets it so `while (true) {}` cannot hang the server."""
        self.write = write or print
        self.read = read or input
        self.time_limit = time_limit
        self.deadline = None
        self.steps = 0
        self.globals = Environment()
        for b in BUILTINS:
            self.globals.define(b.name, b)
        self.depth = 0
        self.loop_depth = 0
        self.fn_depth = 0

    # ---- entry points --------------------------------------------------
    def run(self, source):
        """Lex, parse and execute source code. Returns the value of the
        last expression statement (used by the REPL to echo results)."""
        program = parse(tokenize(source))
        if self.time_limit is not None:
            self.deadline = time.perf_counter() + self.time_limit
        result = None
        for stmt in program:
            result = self.execute(stmt, self.globals)
        return result

    def tick(self, line):
        """Called on every statement and loop iteration to enforce the time limit.
        The clock is only read every 1000 steps to keep this cheap."""
        self.steps += 1
        if self.deadline is not None and self.steps % 1000 == 0 \
                and time.perf_counter() > self.deadline:
            raise LumenRuntimeError(
                f"Time limit exceeded ({self.time_limit:g} s): "
                f"is there an infinite loop?", line)

    # ---- statements ----------------------------------------------------
    def execute(self, node, env):
        self.tick(getattr(node, "line", None))
        method = getattr(self, "exec_" + type(node).__name__)
        return method(node, env)

    def exec_ExprStmt(self, node, env):
        return self.evaluate(node.expr, env)

    def exec_Let(self, node, env):
        value = self.evaluate(node.value, env)
        env.define(node.name, value, node.line)
        return None

    def exec_Block(self, node, env):
        self.execute_block(node.statements, Environment(env))

    def execute_block(self, statements, env):
        for stmt in statements:
            self.execute(stmt, env)

    def exec_If(self, node, env):
        if is_truthy(self.evaluate(node.condition, env)):
            self.execute(node.then_branch, env)
        elif node.else_branch is not None:
            self.execute(node.else_branch, env)

    def exec_While(self, node, env):
        self.loop_depth += 1
        try:
            while is_truthy(self.evaluate(node.condition, env)):
                self.tick(node.line)
                try:
                    self.execute(node.body, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        finally:
            self.loop_depth -= 1

    def exec_For(self, node, env):
        iterable = self.evaluate(node.iterable, env)
        if not isinstance(iterable, (list, str)):
            raise LumenRuntimeError(
                f"Can only loop over a list or string, got {type_name(iterable)}", node.line)
        self.loop_depth += 1
        try:
            for item in list(iterable):         # copy: safe if body mutates list
                loop_env = Environment(env)
                loop_env.define(node.var, item)
                try:
                    self.execute(node.body, loop_env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        finally:
            self.loop_depth -= 1

    def exec_Return(self, node, env):
        if self.fn_depth == 0:
            raise LumenRuntimeError("'return' used outside a function", node.line)
        value = None if node.value is None else self.evaluate(node.value, env)
        raise ReturnSignal(value)

    def exec_Break(self, node, env):
        if self.loop_depth == 0:
            raise LumenRuntimeError("'break' used outside a loop", node.line)
        raise BreakSignal()

    def exec_Continue(self, node, env):
        if self.loop_depth == 0:
            raise LumenRuntimeError("'continue' used outside a loop", node.line)
        raise ContinueSignal()

    # ---- expressions ---------------------------------------------------
    def evaluate(self, node, env):
        method = getattr(self, "eval_" + type(node).__name__)
        return method(node, env)

    def eval_Literal(self, node, env):
        return node.value

    def eval_Variable(self, node, env):
        return env.get(node.name, node.line)

    def eval_Assign(self, node, env):
        value = self.evaluate(node.value, env)
        env.assign(node.name, value, node.line)
        return value

    def eval_ListLiteral(self, node, env):
        return [self.evaluate(item, env) for item in node.items]

    def eval_FunctionExpr(self, node, env):
        return LumenFunction(node, env)

    def eval_Logical(self, node, env):
        left = self.evaluate(node.left, env)
        if node.op == "or":
            return left if is_truthy(left) else self.evaluate(node.right, env)
        return self.evaluate(node.right, env) if is_truthy(left) else left

    def eval_Unary(self, node, env):
        value = self.evaluate(node.operand, env)
        if node.op == "-":
            return -require_number(value, "Operand of '-'", node.line)
        return not is_truthy(value)

    def eval_Binary(self, node, env):
        a = self.evaluate(node.left, env)
        b = self.evaluate(node.right, env)
        op, line = node.op, node.line

        if op == "==":
            return values_equal(a, b)
        if op == "!=":
            return not values_equal(a, b)

        if op == "+":
            if is_number(a) and is_number(b):
                return a + b
            if isinstance(a, str) and isinstance(b, str):
                return a + b
            if isinstance(a, list) and isinstance(b, list):
                return a + b
            raise LumenRuntimeError(
                f"Cannot add {type_name(a)} and {type_name(b)} "
                f"(hint: use str() to convert)", line)

        if op == "*":
            if is_number(a) and is_number(b):
                return a * b
            if isinstance(a, (str, list)) and isinstance(b, int) and not isinstance(b, bool):
                return a * b
            raise LumenRuntimeError(
                f"Cannot multiply {type_name(a)} and {type_name(b)}", line)

        if op in ("<", "<=", ">", ">="):
            same_kind = (is_number(a) and is_number(b)) or \
                        (isinstance(a, str) and isinstance(b, str))
            if not same_kind:
                raise LumenRuntimeError(
                    f"Cannot compare {type_name(a)} and {type_name(b)}", line)
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

        require_number(a, f"Left operand of '{op}'", line)
        require_number(b, f"Right operand of '{op}'", line)
        if op == "-":
            return a - b
        if op == "/":
            if b == 0:
                raise LumenRuntimeError("Division by zero", line)
            if isinstance(a, int) and isinstance(b, int) and a % b == 0:
                return a // b
            return a / b
        if op == "%":
            if b == 0:
                raise LumenRuntimeError("Modulo by zero", line)
            return a % b
        raise LumenRuntimeError(f"Unknown operator '{op}'", line)

    def _check_index(self, target, index, line):
        if not isinstance(target, (list, str)):
            raise LumenRuntimeError(f"Cannot index into {type_name(target)}", line)
        if not isinstance(index, int) or isinstance(index, bool):
            raise LumenRuntimeError(f"Index must be an int, got {type_name(index)}", line)
        if not -len(target) <= index < len(target):
            raise LumenRuntimeError(
                f"Index {index} out of range (length {len(target)})", line)

    def eval_Index(self, node, env):
        target = self.evaluate(node.target, env)
        index = self.evaluate(node.index, env)
        self._check_index(target, index, node.line)
        return target[index]

    def eval_IndexAssign(self, node, env):
        target = self.evaluate(node.target, env)
        index = self.evaluate(node.index, env)
        value = self.evaluate(node.value, env)
        if isinstance(target, str):
            raise LumenRuntimeError("Strings are immutable", node.line)
        self._check_index(target, index, node.line)
        target[index] = value
        return value

    def eval_Call(self, node, env):
        callee = self.evaluate(node.callee, env)
        args = [self.evaluate(a, env) for a in node.args]
        return self.call(callee, args, node.line)

    def call(self, callee, args, line):
        if isinstance(callee, BuiltinFunction):
            if not callee.min_args <= len(args) <= callee.max_args:
                raise LumenRuntimeError(
                    f"{callee.name}() takes {self._arity_text(callee)} "
                    f"argument(s) but {len(args)} were given", line)
            return callee.func(self, args, line)

        if isinstance(callee, LumenFunction):
            if len(args) != callee.arity:
                raise LumenRuntimeError(
                    f"{callee.name}() takes {callee.arity} argument(s) "
                    f"but {len(args)} were given", line)
            if self.depth >= MAX_CALL_DEPTH:
                raise LumenRuntimeError(
                    f"Stack overflow: more than {MAX_CALL_DEPTH} nested calls "
                    f"(missing base case in '{callee.name}'?)", line)
            call_env = Environment(callee.closure)
            for name, value in zip(callee.decl.params, args):
                call_env.define(name, value)

            # A function body starts a fresh loop context: 'break' inside a
            # function must not escape to a loop in the caller.
            saved_loops = self.loop_depth
            self.loop_depth = 0
            self.depth += 1
            self.fn_depth += 1
            try:
                self.execute_block(callee.decl.body, call_env)
            except ReturnSignal as r:
                return r.value
            finally:
                self.depth -= 1
                self.fn_depth -= 1
                self.loop_depth = saved_loops
            return None

        raise LumenRuntimeError(f"'{to_str(callee, True)}' is not a function", line)

    @staticmethod
    def _arity_text(fn):
        if fn.max_args == float("inf"):
            return f"at least {fn.min_args}"
        if fn.min_args == fn.max_args:
            return str(fn.min_args)
        return f"{fn.min_args} to {fn.max_args}"


# Each Lumen call uses several Python frames; give Python enough room.
sys.setrecursionlimit(max(sys.getrecursionlimit(), MAX_CALL_DEPTH * 20))
