"""Flask back end for the Lumen Playground.

Run from the project root:
    pip install -r requirements.txt
    python -m web.app
then open http://localhost:5000

REST API
    GET  /api/examples            list the sample programs in examples/
    POST /api/run                 run code     {code, input}  -> {output, error, time_ms}
    POST /api/tokens              lexer output {code}         -> {tokens} | {error}
    POST /api/ast                 parser output {code}        -> {ast}    | {error}
    POST /api/snippets            save a program {title, code} -> {id, title, created_at}
    GET  /api/snippets            recently saved programs
    GET  /api/snippets/<id>       load a saved program
"""

import dataclasses
import os
import pathlib
import threading
import time

from flask import Flask, jsonify, render_template, request

from lumen import Interpreter, LumenError
from lumen.errors import LumenRuntimeError
from lumen.lexer import tokenize
from lumen.parser import parse

from .database import SnippetStore

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"

MAX_CODE_CHARS = 20_000      # reject very large programs
MAX_TITLE_CHARS = 80
MAX_OUTPUT_LINES = 2_000     # stop programs that print forever
TIME_LIMIT_SECONDS = 3       # stop infinite loops


def create_app(database_path=None):
    app = Flask(__name__)
    app.json.sort_keys = False      # keep AST fields in source order (callee before args)
    store = SnippetStore(database_path or os.environ.get(
        "LUMEN_DB", str(pathlib.Path(__file__).resolve().parent / "lumen.db")))

    # ---- helpers -------------------------------------------------------
    def read_json():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, (jsonify(error="Request body must be a JSON object"), 400)
        return data, None

    def read_code(data):
        code = data.get("code")
        if not isinstance(code, str):
            return None, (jsonify(error="'code' must be a string"), 400)
        if len(code) > MAX_CODE_CHARS:
            return None, (jsonify(error=f"Program is too long (max {MAX_CODE_CHARS} characters)"), 413)
        return code, None

    def error_payload(e):
        return {"message": str(e), "line": e.line, "kind": e.kind}

    # ---- pages ---------------------------------------------------------
    @app.get("/")
    def index():
        return render_template("index.html")

    # ---- API: interpreter ---------------------------------------------
    @app.get("/api/examples")
    def examples():
        items = []
        for path in sorted(EXAMPLES_DIR.glob("*.lm")):
            name = path.stem.split("_", 1)[-1].replace("_", " ").title()
            items.append({"file": path.name, "name": name,
                          "code": path.read_text(encoding="utf-8")})
        return jsonify(examples=items)

    @app.post("/api/run")
    def run():
        data, err = read_json()
        if err:
            return err
        code, err = read_code(data)
        if err:
            return err
        stdin = data.get("input") or ""
        if not isinstance(stdin, str):
            return jsonify(error="'input' must be a string"), 400

        output = []
        input_lines = stdin.splitlines()

        def write(text):
            if len(output) >= MAX_OUTPUT_LINES:
                raise LumenRuntimeError(f"Output limit reached ({MAX_OUTPUT_LINES} lines)")
            output.append(text)

        def read(prompt=""):
            if prompt:
                output.append(prompt)
            if not input_lines:
                raise LumenRuntimeError("input() needs a value: type it in the Input box")
            return input_lines.pop(0)

        interp = Interpreter(write=write, read=read, time_limit=TIME_LIMIT_SECONDS)
        start = time.perf_counter()
        error = None
        try:
            interp.run(code)
        except LumenError as e:
            error = error_payload(e)
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        return jsonify(output=output, error=error, time_ms=elapsed)

    @app.post("/api/tokens")
    def tokens():
        data, err = read_json()
        if err:
            return err
        code, err = read_code(data)
        if err:
            return err
        try:
            toks = tokenize(code)
        except LumenError as e:
            return jsonify(error=error_payload(e))
        return jsonify(tokens=[{"type": t.type.name, "lexeme": t.lexeme, "line": t.line}
                               for t in toks])

    @app.post("/api/ast")
    def ast():
        data, err = read_json()
        if err:
            return err
        code, err = read_code(data)
        if err:
            return err
        try:
            program = parse(tokenize(code))
        except LumenError as e:
            return jsonify(error=error_payload(e))
        return jsonify(ast=[node_to_dict(n) for n in program])

    # ---- API: saved programs (database) --------------------------------
    @app.post("/api/snippets")
    def save_snippet():
        data, err = read_json()
        if err:
            return err
        code, err = read_code(data)
        if err:
            return err
        if not code.strip():
            return jsonify(error="Cannot save an empty program"), 400
        title = str(data.get("title") or "Untitled program").strip()[:MAX_TITLE_CHARS]
        return jsonify(store.save(title or "Untitled program", code)), 201

    @app.get("/api/snippets")
    def list_snippets():
        return jsonify(snippets=store.recent())

    @app.get("/api/snippets/<snippet_id>")
    def get_snippet(snippet_id):
        snippet = store.get(snippet_id)
        if snippet is None:
            return jsonify(error="No saved program with that id"), 404
        return jsonify(snippet)

    return app


def node_to_dict(node):
    """Convert an AST dataclass tree into plain JSON-friendly dicts."""
    if dataclasses.is_dataclass(node):
        out = {"node": type(node).__name__}
        for f in dataclasses.fields(node):
            out[f.name] = node_to_dict(getattr(node, f.name))
        return out
    if isinstance(node, list):
        return [node_to_dict(n) for n in node]
    return node


if __name__ == "__main__":
    # Lumen allows 1000 nested calls; each uses several Python frames.
    # Windows gives threads a small stack by default, so ask for a bigger one.
    threading.stack_size(64 * 1024 * 1024)
    port = int(os.environ.get("PORT", 5000))
    print(f"Lumen Playground running at http://localhost:{port}")
    create_app().run(host="127.0.0.1", port=port, debug=False, threaded=True)
