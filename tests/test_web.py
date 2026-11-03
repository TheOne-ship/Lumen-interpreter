"""Tests for the Flask REST API and the SQLite storage (web/)."""

import os
import tempfile
import unittest

try:
    from web.app import create_app
    HAVE_FLASK = True
except ImportError:           # Flask not installed: skip these tests
    HAVE_FLASK = False


@unittest.skipUnless(HAVE_FLASK, "Flask is not installed (pip install -r requirements.txt)")
class WebApiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.client = create_app(self.db_path).test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def run_code(self, code, stdin=""):
        res = self.client.post("/api/run", json={"code": code, "input": stdin})
        self.assertEqual(res.status_code, 200)
        return res.get_json()

    # ---- pages and examples ---------------------------------------------
    def test_index_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Lumen Playground", res.data)

    def test_examples_endpoint(self):
        data = self.client.get("/api/examples").get_json()
        files = [e["file"] for e in data["examples"]]
        self.assertIn("01_hello.lm", files)
        self.assertTrue(all(e["code"] for e in data["examples"]))

    # ---- running code ---------------------------------------------------
    def test_run_success(self):
        data = self.run_code('print("Hi", 2 + 3);')
        self.assertEqual(data["output"], ["Hi 5"])
        self.assertIsNone(data["error"])

    def test_run_reports_error_with_line(self):
        data = self.run_code('print("ok");\nprint(1 / 0);')
        self.assertEqual(data["output"], ["ok"])
        self.assertEqual(data["error"]["line"], 2)
        self.assertIn("Division by zero", data["error"]["message"])

    def test_run_with_input(self):
        data = self.run_code('let n = input("Name? "); print("Hi " + n);', "Asha")
        self.assertEqual(data["output"], ["Name? ", "Hi Asha"])

    def test_missing_input_is_an_error(self):
        data = self.run_code("input();")
        self.assertIn("Input box", data["error"]["message"])

    def test_infinite_loop_is_stopped(self):
        data = self.run_code("while (true) { }")
        self.assertIn("Time limit exceeded", data["error"]["message"])

    def test_output_limit(self):
        data = self.run_code("while (true) { print(1); }")
        self.assertIn("Output limit", data["error"]["message"])

    def test_bad_requests(self):
        self.assertEqual(self.client.post("/api/run", data="not json").status_code, 400)
        self.assertEqual(self.client.post("/api/run", json={"code": 5}).status_code, 400)
        self.assertEqual(self.client.post("/api/run", json={"code": "x" * 30000}).status_code, 413)

    # ---- tokens and AST ---------------------------------------------------
    def test_tokens(self):
        data = self.client.post("/api/tokens", json={"code": "let x = 1;"}).get_json()
        self.assertEqual([t["type"] for t in data["tokens"]],
                         ["LET", "IDENT", "ASSIGN", "NUMBER", "SEMICOLON", "EOF"])

    def test_ast(self):
        data = self.client.post("/api/ast", json={"code": "1 + 2 * 3;"}).get_json()
        expr = data["ast"][0]["expr"]
        self.assertEqual((expr["node"], expr["op"], expr["right"]["op"]), ("Binary", "+", "*"))

    def test_ast_syntax_error(self):
        data = self.client.post("/api/ast", json={"code": "let = ;"}).get_json()
        self.assertEqual(data["error"]["kind"], "SyntaxError")

    # ---- saved programs (database) ---------------------------------------
    def test_save_and_load_snippet(self):
        res = self.client.post("/api/snippets", json={"title": "Demo", "code": "print(1);"})
        self.assertEqual(res.status_code, 201)
        snippet_id = res.get_json()["id"]

        loaded = self.client.get(f"/api/snippets/{snippet_id}").get_json()
        self.assertEqual((loaded["title"], loaded["code"]), ("Demo", "print(1);"))

        recent = self.client.get("/api/snippets").get_json()["snippets"]
        self.assertEqual(recent[0]["id"], snippet_id)

    def test_unknown_snippet(self):
        self.assertEqual(self.client.get("/api/snippets/nope").status_code, 404)

    def test_empty_program_not_saved(self):
        res = self.client.post("/api/snippets", json={"title": "x", "code": "   "})
        self.assertEqual(res.status_code, 400)

    def test_sql_injection_is_harmless(self):
        title = "x'); DROP TABLE snippets; --"
        res = self.client.post("/api/snippets", json={"title": title, "code": "print(1);"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.client.get("/api/snippets").get_json()["snippets"][0]["title"], title)


if __name__ == "__main__":
    unittest.main()
