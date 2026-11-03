# Lumen Language Guide

A complete reference for the Lumen language.

## 1. Basics

- Statements end with `;` (optional just before `}` or at the end of input).
- Comments start with `#` and run to the end of the line.
- Identifiers: letters, digits and `_`, not starting with a digit.

## 2. Data types

| Type       | Examples                 | Notes                                   |
|------------|--------------------------|-----------------------------------------|
| `int`      | `0`, `42`, `-7`          | Arbitrary size (backed by Python `int`) |
| `float`    | `3.14`, `0.5`            |                                         |
| `string`   | `"hi"`, `"a\tb\n"`       | Escapes: `\n` `\t` `\"` `\\`            |
| `bool`     | `true`, `false`          |                                         |
| `nil`      | `nil`                    | "No value"                              |
| `list`     | `[1, "two", [3]]`        | Mutable, can mix types                  |
| `function` | `fn (x) { return x; }`   | First-class values                      |

**Truthiness:** `false`, `nil`, `0`, `""` and `[]` are falsy. Everything else is truthy.

## 3. Variables

```
let x = 10;      # declare
x = x + 1;       # reassign (variable must already be declared)
```

Each `{ ... }` block creates a new scope. An inner `let` can shadow an outer variable.

## 4. Operators (highest precedence first)

| Operators                    | Meaning                                  |
|------------------------------|------------------------------------------|
| `f(x)`  `a[i]`               | call, index                              |
| `-x`  `!x`  `not x`          | negate, logical not                      |
| `*`  `/`  `%`                | multiply (also repeats strings/lists), divide, modulo |
| `+`  `-`                     | add (also joins strings/lists), subtract |
| `<`  `<=`  `>`  `>=`         | compare numbers or strings               |
| `==`  `!=`                   | equality (works on all types)            |
| `and`                        | logical and (short-circuit)              |
| `or`                         | logical or (short-circuit)               |
| `=`                          | assignment (right-associative)           |

`/` gives an `int` when the division is exact (`8 / 2` is `4`), otherwise a `float` (`7 / 2` is `3.5`).

## 5. Control flow

```
if (score >= 40) {
    print("pass");
} else if (score >= 35) {
    print("grace");
} else {
    print("fail");
}

while (n > 0) { n = n - 1; }

for (item in [10, 20, 30]) { print(item); }
for (ch in "abc") { print(ch); }
for (i in range(5)) {
    if (i == 1) { continue; }
    if (i == 3) { break; }
}
```

## 6. Functions

```
fn add(a, b) {
    return a + b;
}

let square = fn (x) { return x * x; };   # anonymous function

fn make_counter() {                     # closure
    let count = 0;
    return fn () { count = count + 1; return count; };
}
```

A function without `return` gives `nil`. Recursion depth is limited to 1000 calls. Going deeper reports a "Stack overflow" error instead of crashing.

## 7. Lists

```
let xs = [3, 1, 2];
xs[0] = 7;           # index assignment
print(xs[-1]);       # negative index counts from the end -> 2
push(xs, 9);         # append
let last = pop(xs);  # remove and return last item
let zeros = [0] * 5; # [0, 0, 0, 0, 0]
```

## 8. Built-in functions

| Function                  | Description                                    |
|---------------------------|------------------------------------------------|
| `print(a, b, ...)`        | Print values separated by spaces               |
| `input(prompt?)`          | Read a line from the keyboard (as a string)    |
| `len(x)`                  | Length of a string or list                     |
| `str(x)` `int(x)` `float(x)` | Type conversion                             |
| `type(x)`                 | Type name as a string, e.g. `"list"`           |
| `range(n)` `range(a, b)` `range(a, b, step)` | List of integers            |
| `push(list, x)` `pop(list)` | Add / remove at the end of a list            |
| `join(list, sep)`         | Join items into a string                       |
| `split(text, sep?)`       | Split a string into a list                     |
| `sqrt(x)` `abs(x)`        | Maths helpers                                  |
| `clock()`                 | Seconds counter, for timing code               |

## 9. Errors

Every error shows the line number and a description:

```
[line 7] RuntimeError: Index 3 out of range (length 3)
[line 2] SyntaxError: Expected ';' after statement, found 'let'
```

## 10. Formal grammar

```
program     -> declaration* EOF
declaration -> fnDecl | letDecl | statement
fnDecl      -> "fn" IDENT "(" params? ")" block
letDecl     -> "let" IDENT "=" expression ";"
statement   -> ifStmt | whileStmt | forStmt | returnStmt
             | "break" ";" | "continue" ";" | block | exprStmt
ifStmt      -> "if" "(" expression ")" statement ( "else" statement )?
whileStmt   -> "while" "(" expression ")" statement
forStmt     -> "for" "(" IDENT "in" expression ")" statement
returnStmt  -> "return" expression? ";"
block       -> "{" declaration* "}"

expression  -> assignment
assignment  -> ( IDENT | call "[" expression "]" ) "=" assignment | or
or          -> and ( "or" and )*
and         -> equality ( "and" equality )*
equality    -> comparison ( ( "==" | "!=" ) comparison )*
comparison  -> term ( ( "<" | "<=" | ">" | ">=" ) term )*
term        -> factor ( ( "+" | "-" ) factor )*
factor      -> unary ( ( "*" | "/" | "%" ) unary )*
unary       -> ( "-" | "!" | "not" ) unary | call
call        -> primary ( "(" args? ")" | "[" expression "]" )*
primary     -> NUMBER | STRING | "true" | "false" | "nil" | IDENT
             | "(" expression ")" | "[" args? "]"
             | "fn" "(" params? ")" block
```
