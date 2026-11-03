import unittest

from lumen.errors import LumenRuntimeError

from .helpers import run


class ArithmeticAndValues(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(run("print(2 + 3 * 4, (2 + 3) * 4, 10 % 3, -5 + 2);"),
                         ["14 20 1 -3"])

    def test_division(self):
        self.assertEqual(run("print(8 / 2, 7 / 2);"), ["4 3.5"])

    def test_strings(self):
        self.assertEqual(run('print("ab" + "cd", "-" * 3, len("hello"), "hey"[1]);'),
                         ["abcd --- 5 e"])

    def test_truthiness(self):
        self.assertEqual(run('print(not 0, not "", not [], not nil, not 1, not "x");'),
                         ["true true true true false false"])

    def test_equality_does_not_mix_bool_and_number(self):
        self.assertEqual(run("print(1 == true, 1 == 1.0, [1, 2] == [1, 2]);"),
                         ["false true true"])

    def test_short_circuit(self):
        # crash() is never called because the left side decides the result
        self.assertEqual(run("print(false and crash(), true or crash());"),
                         ["false true"])


class Variables(unittest.TestCase):
    def test_block_scope_shadowing(self):
        src = "let x = 1; { let x = 2; print(x); } print(x);"
        self.assertEqual(run(src), ["2", "1"])

    def test_assignment_updates_outer_variable(self):
        self.assertEqual(run("let x = 1; { x = 5; } print(x);"), ["5"])

    def test_undefined_variable(self):
        with self.assertRaises(LumenRuntimeError) as ctx:
            run("print(y);")
        self.assertIn("Undefined variable 'y'", str(ctx.exception))

    def test_assign_without_let(self):
        with self.assertRaises(LumenRuntimeError):
            run("z = 3;")


class ControlFlow(unittest.TestCase):
    def test_if_else_chain(self):
        src = """
        fn sign(n) {
            if (n > 0) { return "pos"; } else if (n < 0) { return "neg"; } else { return "zero"; }
        }
        print(sign(5), sign(-2), sign(0));
        """
        self.assertEqual(run(src), ["pos neg zero"])

    def test_while_loop(self):
        self.assertEqual(run("let i = 0; let s = 0; while (i < 5) { s = s + i; i = i + 1; } print(s);"),
                         ["10"])

    def test_for_break_continue(self):
        src = "for (i in range(10)) { if (i % 2 == 0) { continue; } if (i > 7) { break; } print(i); }"
        self.assertEqual(run(src), ["1", "3", "5", "7"])

    def test_for_over_string(self):
        self.assertEqual(run('let s = ""; for (c in "abc") { s = c + s; } print(s);'), ["cba"])

    def test_break_outside_loop(self):
        with self.assertRaises(LumenRuntimeError):
            run("break;")

    def test_return_outside_function(self):
        with self.assertRaises(LumenRuntimeError):
            run("return 1;")


class Functions(unittest.TestCase):
    def test_recursion(self):
        src = "fn fib(n) { if (n < 2) { return n; } return fib(n-1) + fib(n-2); } print(fib(15));"
        self.assertEqual(run(src), ["610"])

    def test_closure_counter(self):
        src = """
        fn counter() { let c = 0; return fn () { c = c + 1; return c; }; }
        let a = counter(); let b = counter();
        a(); a();
        print(a(), b());
        """
        self.assertEqual(run(src), ["3 1"])

    def test_higher_order_function(self):
        src = "fn twice(f, x) { return f(f(x)); } print(twice(fn (n) { return n * 3; }, 2));"
        self.assertEqual(run(src), ["18"])

    def test_function_without_return_gives_nil(self):
        self.assertEqual(run("fn f() { } print(f());"), ["nil"])

    def test_wrong_argument_count(self):
        with self.assertRaises(LumenRuntimeError) as ctx:
            run("fn f(a, b) { } f(1);")
        self.assertIn("takes 2 argument(s) but 1", str(ctx.exception))

    def test_stack_overflow_is_reported(self):
        with self.assertRaises(LumenRuntimeError) as ctx:
            run("fn forever(n) { return forever(n + 1); } forever(0);")
        self.assertIn("Stack overflow", str(ctx.exception))

    def test_break_does_not_escape_function(self):
        with self.assertRaises(LumenRuntimeError):
            run("fn f() { break; } for (i in [1]) { f(); }")

    def test_calling_non_function(self):
        with self.assertRaises(LumenRuntimeError):
            run("let x = 5; x();")


class ListsAndBuiltins(unittest.TestCase):
    def test_list_operations(self):
        src = "let xs = [1, 2]; push(xs, 3); xs[0] = 10; print(xs, len(xs), xs[-1]); print(pop(xs), xs);"
        self.assertEqual(run(src), ["[10, 2, 3] 3 3", "3 [10, 2]"])

    def test_nested_lists(self):
        self.assertEqual(run('let m = [[1, 2], [3, 4]]; m[1][0] = 9; print(m, ["a"]);'),
                         ['[[1, 2], [9, 4]] ["a"]'])

    def test_index_out_of_range(self):
        with self.assertRaises(LumenRuntimeError) as ctx:
            run("let xs = [1]; print(xs[5]);")
        self.assertIn("out of range", str(ctx.exception))

    def test_conversions(self):
        self.assertEqual(run('print(int("42") + 1, float("2.5"), str(7) + "!", type([]));'),
                         ["43 2.5 7! list"])

    def test_range_variants(self):
        self.assertEqual(run("print(range(3), range(2, 5), range(10, 0, -3));"),
                         ["[0, 1, 2] [2, 3, 4] [10, 7, 4, 1]"])

    def test_join_and_split(self):
        self.assertEqual(run('print(join(split("a,b,c", ","), "-"));'), ["a-b-c"])

    def test_input(self):
        self.assertEqual(run('let n = input("Name? "); print("Hi " + n);', inputs=["Asha"]),
                         ["Hi Asha"])

    def test_type_errors(self):
        for src in ['print("a" + 1);', "print(-\"x\");", 'print(1 < "2");', "print(5 / 0);"]:
            with self.subTest(src=src), self.assertRaises(LumenRuntimeError):
                run(src)

    def test_error_reports_line_number(self):
        with self.assertRaises(LumenRuntimeError) as ctx:
            run("let a = 1;\nlet b = 2;\nprint(a / 0);")
        self.assertEqual(ctx.exception.line, 3)


if __name__ == "__main__":
    unittest.main()
