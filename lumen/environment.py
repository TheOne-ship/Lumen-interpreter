"""Variable scopes.

Each block or function call gets its own Environment that points to the
enclosing one. Looking up a name walks outwards until it is found, which
is what gives Lumen lexical scoping and closures.
"""

from .errors import LumenRuntimeError


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value, line=None):
        if name in self.values and self.parent is not None:
            raise LumenRuntimeError(
                f"Variable '{name}' is already declared in this scope", line)
        self.values[name] = value

    def get(self, name, line=None):
        env = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise LumenRuntimeError(f"Undefined variable '{name}'", line)

    def assign(self, name, value, line=None):
        env = self
        while env is not None:
            if name in env.values:
                env.values[name] = value
                return
            env = env.parent
        raise LumenRuntimeError(
            f"Cannot assign to undeclared variable '{name}' (use 'let' first)", line)
