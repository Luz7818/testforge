"""Map a unified diff to changed functions — the PR-gate's target discovery.

Pure stdlib, pure functions: ``parse_diff`` turns a unified diff into per-file
changed-line sets (new-side numbering), ``changed_functions`` intersects those
with the functions actually defined in the changed files. Deterministic; a
function is "changed" when any of its body lines (1-based, inclusive span) was
added or modified on the PR side. Pure deletions never create targets.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FunctionSpan:
    name: str
    lineno: int
    end_lineno: int

    @property
    def lines(self) -> set[int]:
        return set(range(self.lineno, self.end_lineno + 1))


@dataclass
class ChangedFunction:
    file: str          # repo-relative posix path
    function: FunctionSpan
    changed_lines: set[int]   # the PR-side changed lines inside the function

    @property
    def qualified(self) -> str:
        stem = Path(self.file).stem
        return f"{stem}.{self.function.name}"


def parse_diff(diff_text: str) -> dict[str, set[int]]:
    """Unified diff -> {file: changed new-side line numbers}.

    Handles ``+++ b/<path>`` headers and ``@@ -a[,b] +c[,d] @@`` hunks; context
    lines and deletions consume no new-side lines. Files without new content
    (pure deletions, /dev/null) yield empty sets.
    """
    out: dict[str, set[int]] = {}
    current_file: str | None = None
    new_start = 0
    new_count = 0
    in_hunk = False
    new_line = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            current_file = None if path == "/dev/null" else _strip_b_prefix(path)
            in_hunk = False
        elif raw.startswith("@@"):
            m = _HUNK_RE.match(raw)
            if m and current_file is not None:
                new_start = int(m.group("start"))
                new_count = int(m.group("count") or "1")
                new_line = new_start
                in_hunk = new_count > 0
                out.setdefault(current_file, set())
        elif in_hunk and current_file is not None:
            if raw.startswith("+"):
                out[current_file].add(new_line)
                new_line += 1
            elif raw.startswith("-") or raw.startswith("\\"):
                pass  # deletion / "\ No newline": consumes no new-side line
            else:
                new_line += 1
    return out


_HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


def _strip_b_prefix(path: str) -> str:
    return path[2:] if path.startswith("b/") else path


def functions_in_source(source: str) -> list[FunctionSpan]:
    """Top-level functions of a module (nested functions are part of their
    parent's span via end_lineno, so they need no separate entry)."""
    spans: list[FunctionSpan] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return spans
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            end = getattr(node, "end_lineno", None) or node.lineno
            spans.append(FunctionSpan(name=node.name, lineno=node.lineno, end_lineno=end))
    return spans


def changed_functions(
    diff_text: str,
    root: Path | None = None,
    *,
    skip_tests: bool = True,
) -> list[ChangedFunction]:
    """Changed functions of a diff, resolved against ``root`` (default cwd).

    Non-Python files and test modules are skipped; a changed file that no
    longer parses (deleted, syntax-broken) contributes no targets. Sorted by
    (file, line) so the discovery output is deterministic.
    """
    root = root or Path.cwd()
    found: list[ChangedFunction] = []
    for file, lines in sorted(parse_diff(diff_text).items()):
        if not file.endswith(".py"):
            continue
        if skip_tests and Path(file).name.startswith("test_"):
            continue
        path = root / file
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for span in functions_in_source(source):
            hit = lines & span.lines
            if hit:
                found.append(ChangedFunction(file=file, function=span, changed_lines=hit))
    found.sort(key=lambda c: (c.file, c.function.lineno))
    return found
