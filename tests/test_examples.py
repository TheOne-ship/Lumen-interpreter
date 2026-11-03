"""Make sure every example program runs (06_errors.lm is expected to fail)."""

import pathlib
import unittest

from lumen.errors import LumenRuntimeError

from .helpers import run

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


class ExampleProgramTests(unittest.TestCase):
    def test_examples_run(self):
        for path in sorted(EXAMPLES.glob("*.lm")):
            source = path.read_text(encoding="utf-8")
            with self.subTest(example=path.name):
                if path.name == "06_errors.lm":
                    with self.assertRaises(LumenRuntimeError):
                        run(source)
                else:
                    self.assertTrue(run(source))

    def test_hello_output(self):
        out = run((EXAMPLES / "01_hello.lm").read_text(encoding="utf-8"))
        self.assertEqual(out[0], "Hello, World!")


if __name__ == "__main__":
    unittest.main()
