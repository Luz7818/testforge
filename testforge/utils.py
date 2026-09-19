"""Small shared helpers: workspaces, diffs, serialization."""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from difflib import unified_diff
from pathlib import Path


def new_work_root(prefix: str = "tf") -> Path:
    root = Path(tempfile.gettempdir()) / f"{prefix}_{uuid.uuid4().hex[:10]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextlib.contextmanager
def workspace(module_source: str, module_name: str, test_files: dict[str, str]):
    """A throwaway directory where ``module_name.py`` plus the given test
    files are importable together. Removed on exit."""
    root = new_work_root()
    try:
        (root / f"{module_name}.py").write_text(
            module_source, encoding="utf-8"
        )
        for fname, code in test_files.items():
            (root / fname).write_text(code, encoding="utf-8")
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_cmd(
    args: list[str],
    cwd: Path,
    timeout: float,
) -> tuple[int, str]:
    """Run a subprocess, capturing combined output. Returns (returncode, output).

    A timeout is reported as returncode -9 (never produced by real exits).
    The environment is inherited (pytest/coverage need TEMP, SYSTEMROOT, ...)
    with Python-encoding overrides applied.
    """
    import os

    cmd = [sys.executable, *args]
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"


def mini_diff(original_source: str, mutated_source: str, context: int = 2) -> str:
    """A short unified diff used both for logs and for LLM feedback prompts."""
    lines = list(
        unified_diff(
            original_source.splitlines(keepends=True),
            mutated_source.splitlines(keepends=True),
            fromfile="original",
            tofile="mutant",
            n=context,
        )
    )
    return "".join(lines)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
