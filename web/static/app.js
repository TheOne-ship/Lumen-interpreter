// Lumen Playground front end: talks to the Flask REST API in web/app.py
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const code = $("code"), highlight = $("highlight"), gutter = $("gutter");
  const output = $("output"), statusBar = $("status"), stdin = $("stdin");

  const KEYWORDS = new Set(["let", "fn", "return", "if", "else", "while", "for", "in",
                            "break", "continue", "and", "or", "not"]);
  const LITERALS = new Set(["true", "false", "nil"]);
  const BUILTINS = new Set(["print", "input", "len", "str", "int", "float", "type", "range",
                            "push", "pop", "join", "split", "sqrt", "abs", "clock"]);

  const STARTER = `# Welcome to the Lumen Playground!
# Edit this program and press Run (Ctrl+Enter).

fn greet(name) {
    return "Hello, " + name + "!";
}

print(greet("Full Stack"));

let squares = [];
for (n in range(1, 6)) {
    push(squares, n * n);
}
print("Squares:", squares);
`;

  let errorLine = null;
  let currentFile = "untitled.lm";

  // ---- API helper ------------------------------------------------------
  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    };
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ error: `Server error (${res.status})` }));
    if (!res.ok && !data.error) data.error = `Server error (${res.status})`;
    return data;
  }

  // ---- editor: highlighting, gutter, scroll sync -------------------------
  const escapeHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function highlightCode(src) {
    const re = /(#[^\n]*)|("(?:\\.|[^"\\\n])*"?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g;
    let html = "", last = 0, m;
    while ((m = re.exec(src)) !== null) {
      html += escapeHtml(src.slice(last, m.index));
      const text = escapeHtml(m[0]);
      let cls = null;
      if (m[1]) cls = "com";
      else if (m[2]) cls = "str";
      else if (m[3]) cls = "num";
      else if (KEYWORDS.has(m[0])) cls = "kw";
      else if (LITERALS.has(m[0])) cls = "lit";
      else if (BUILTINS.has(m[0]) || src[re.lastIndex] === "(") cls = "fn";
      html += cls ? `<span class="tok-${cls}">${text}</span>` : text;
      last = re.lastIndex;
    }
    html += escapeHtml(src.slice(last));
    return html + "\n";             // keeps the last empty line the same height
  }

  function refreshEditor() {
    highlight.innerHTML = highlightCode(code.value);
    const lines = code.value.split("\n").length;
    let g = "";
    for (let i = 1; i <= lines; i++) {
      g += `<div${i === errorLine ? ' class="err"' : ""}>${i}</div>`;
    }
    gutter.innerHTML = g;
    syncScroll();
  }

  function syncScroll() {
    highlight.parentElement.scrollTop = code.scrollTop;
    highlight.parentElement.scrollLeft = code.scrollLeft;
    gutter.scrollTop = code.scrollTop;
  }

  function updateCursor() {
    const before = code.value.slice(0, code.selectionStart).split("\n");
    $("cursor-pos").textContent = `Ln ${before.length}, Col ${before.at(-1).length + 1}`;
  }

  function setCode(text, fileName) {
    code.value = text;
    currentFile = fileName || "untitled.lm";
    $("file-label").textContent = currentFile;
    errorLine = null;
    refreshEditor();
    code.scrollTop = 0;
    updateCursor();
    // a new program starts with a clean output panel
    output.innerHTML = '<span class="muted">Press Run to execute your program.</span>';
    setStatus("Ready");
    if (activeTab === "tokens") showTokens();
    if (activeTab === "ast") showAst();
  }

  code.addEventListener("input", () => { errorLine = null; refreshEditor(); updateCursor(); });
  code.addEventListener("scroll", syncScroll);
  code.addEventListener("click", updateCursor);
  code.addEventListener("keyup", updateCursor);
  code.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {                     // indent with 4 spaces
      e.preventDefault();
      const { selectionStart: s, selectionEnd: t } = code;
      code.setRangeText("    ", s, t, "end");
      code.dispatchEvent(new Event("input"));
    }
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); runProgram(); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); saveProgram(); }
  });

  // ---- tabs ---------------------------------------------------------------
  let activeTab = "output";
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTab = btn.dataset.tab;
      document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
      ["output", "tokens", "ast"].forEach((t) => $("tab-" + t).classList.toggle("hidden", t !== activeTab));
      if (activeTab === "tokens") showTokens();
      if (activeTab === "ast") showAst();
    });
  });

  function setStatus(text, kind) {
    statusBar.textContent = text;
    statusBar.className = "status" + (kind ? " " + kind : "");
  }

  function showError(container, err) {
    const box = document.createElement("div");
    box.className = "err";
    box.textContent = err.message;
    container.appendChild(box);
    if (err.line) { errorLine = err.line; refreshEditor(); }
  }

  // ---- run ------------------------------------------------------------------
  async function runProgram() {
    const btn = $("run-btn");
    btn.disabled = true;
    setStatus("Running…");
    errorLine = null;
    try {
      const res = await api("/api/run", { code: code.value, input: stdin.value });
      output.innerHTML = "";
      if (res.error && !res.output) {            // request-level error (400 etc.)
        showError(output, { message: res.error });
        setStatus("Request failed", "bad");
        return;
      }
      for (const line of res.output) {
        const div = document.createElement("div");
        div.className = "line";
        div.textContent = line;
        output.appendChild(div);
      }
      if (!res.output.length && !res.error) {
        output.innerHTML = '<span class="muted">(no output)</span>';
      }
      if (res.error) {
        showError(output, res.error);
        setStatus(`${res.error.kind} after ${res.time_ms} ms`, "bad");
      } else {
        setStatus(`Finished in ${res.time_ms} ms`, "ok");
      }
      refreshEditor();
      if (activeTab !== "output") document.querySelector('[data-tab="output"]').click();
    } catch (e) {
      output.innerHTML = "";
      showError(output, { message: "Cannot reach the server. Is `python -m web.app` running?" });
      setStatus("Offline", "bad");
    } finally {
      btn.disabled = false;
    }
  }

  // ---- tokens tab -------------------------------------------------------------
  async function showTokens() {
    const box = $("tokens");
    const res = await api("/api/tokens", { code: code.value });
    box.innerHTML = "";
    if (res.error) { showError(box, typeof res.error === "string" ? { message: res.error } : res.error); return; }
    const rows = res.tokens.map((t) =>
      `<tr><td>${t.line}</td><td>${t.type}</td><td>${escapeHtml(t.lexeme)}</td></tr>`).join("");
    box.innerHTML = `<table class="tokens"><thead><tr><th>Line</th><th>Type</th><th>Lexeme</th></tr></thead><tbody>${rows}</tbody></table>`;
    setStatus(`${res.tokens.length} tokens`);
  }

  // ---- syntax tree tab --------------------------------------------------------
  const isNode = (v) => v && typeof v === "object" && !Array.isArray(v) && v.node;

  function scalar(v) {
    if (v === null) return "nil";
    if (typeof v === "string") return JSON.stringify(v);
    if (v === true || v === false) return String(v);
    return String(v);
  }

  const SKIP = ["node", "line", "op", "name", "var"];
  function hasChildren(n) {
    return Object.entries(n).some(([key, v]) =>
      !SKIP.includes(key) && (isNode(v) || Array.isArray(v) ||
        (key !== "value" && v !== null && v !== undefined)));
  }

  function renderNode(n, label, depth) {
    const leaf = !hasChildren(n);
    const det = document.createElement(leaf ? "div" : "details");
    if (leaf) det.className = "leaf-node";
    else if (depth < 3) det.open = true;
    const sum = document.createElement(leaf ? "div" : "summary");
    const inline = [];
    for (const key of ["op", "name", "var", "value"]) {
      if (key in n && !isNode(n[key]) && !Array.isArray(n[key])) inline.push(`${key}=${escapeHtml(scalar(n[key]))}`);
    }
    sum.innerHTML = (label ? `<span class="field">${label}: </span>` : "") +
      `<span class="node">${n.node}</span>` +
      (inline.length ? ` <span class="val">${inline.join("  ")}</span>` : "") +
      (n.line ? ` <span class="field">· line ${n.line}</span>` : "");
    det.appendChild(sum);
    for (const [key, v] of Object.entries(n)) {
      if (SKIP.includes(key)) continue;
      if (key === "value" && !isNode(v) && !Array.isArray(v)) continue;
      if (isNode(v)) det.appendChild(renderNode(v, key, depth + 1));
      else if (Array.isArray(v)) {
        if (!v.length) { appendLeaf(det, `${key}: []`); continue; }
        v.forEach((item, i) => {
          if (isNode(item)) det.appendChild(renderNode(item, `${key}[${i}]`, depth + 1));
          else appendLeaf(det, `${key}[${i}]: ${scalar(item)}`);
        });
      } else if (v !== null && v !== undefined) appendLeaf(det, `${key}: ${scalar(v)}`);
    }
    return det;
  }

  function appendLeaf(parent, text) {
    const d = document.createElement("div");
    d.className = "leaf field";
    d.textContent = text;
    parent.appendChild(d);
  }

  async function showAst() {
    const box = $("ast");
    const res = await api("/api/ast", { code: code.value });
    box.innerHTML = "";
    if (res.error) { showError(box, typeof res.error === "string" ? { message: res.error } : res.error); return; }
    res.ast.forEach((n, i) => box.appendChild(renderNode(n, `statement ${i + 1}`, 0)));
    if (!res.ast.length) box.innerHTML = '<span class="muted">(empty program)</span>';
    setStatus(`${res.ast.length} top-level statements`);
  }

  // ---- examples and saved programs (database) ---------------------------------
  function markActive(listId, btn) {
    document.querySelectorAll(".list button").forEach((b) => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
  }

  async function loadExamples() {
    const list = $("examples");
    try {
      const res = await api("/api/examples");
      list.innerHTML = "";
      for (const ex of res.examples) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.textContent = ex.name;
        btn.title = ex.file;
        btn.addEventListener("click", () => {
          setCode(ex.code, ex.file);
          markActive("examples", btn);
          history.replaceState(null, "", location.pathname);
        });
        li.appendChild(btn);
        list.appendChild(li);
      }
    } catch { list.innerHTML = '<li class="muted">Unavailable</li>'; }
  }

  async function loadSaved() {
    const list = $("saved");
    try {
      const res = await api("/api/snippets");
      list.innerHTML = "";
      if (!res.snippets.length) { list.innerHTML = '<li class="muted">Nothing saved yet</li>'; return; }
      for (const s of res.snippets) {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.innerHTML = `${escapeHtml(s.title)}<small>${s.created_at.slice(0, 16).replace("T", " ")} UTC</small>`;
        btn.addEventListener("click", () => openSnippet(s.id, btn));
        li.appendChild(btn);
        list.appendChild(li);
      }
    } catch { list.innerHTML = '<li class="muted">Unavailable</li>'; }
  }

  async function openSnippet(id, btn) {
    const res = await api(`/api/snippets/${encodeURIComponent(id)}`);
    if (res.error) { toast(res.error); return; }
    setCode(res.code, `${res.title}.lm`);
    markActive("saved", btn);
    history.replaceState(null, "", `?s=${encodeURIComponent(id)}`);
  }

  async function saveProgram() {
    const suggested = currentFile.replace(/\.lm$/, "");
    const title = prompt("Name this program:", suggested === "untitled" ? "" : suggested);
    if (title === null) return;
    const res = await api("/api/snippets", { title, code: code.value });
    if (res.error) { toast(res.error); return; }
    const link = `${location.origin}${location.pathname}?s=${res.id}`;
    history.replaceState(null, "", `?s=${res.id}`);
    currentFile = `${res.title}.lm`;
    $("file-label").textContent = currentFile;
    try { await navigator.clipboard.writeText(link); } catch { /* clipboard may be blocked */ }
    toast(`Saved. Share link copied: <a href="${link}">${link}</a>`);
    loadSaved();
  }

  let toastTimer;
  function toast(html) {
    const t = $("toast");
    t.innerHTML = html;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 5000);
  }

  // ---- buttons and start-up -------------------------------------------------
  $("run-btn").addEventListener("click", runProgram);
  $("save-btn").addEventListener("click", saveProgram);
  $("clear-btn").addEventListener("click", () => {
    output.innerHTML = '<span class="muted">Output cleared.</span>';
    setStatus("Ready");
  });

  const shared = new URLSearchParams(location.search).get("s");
  setCode(STARTER);
  loadExamples();
  loadSaved();
  if (shared) openSnippet(shared, null);
})();
