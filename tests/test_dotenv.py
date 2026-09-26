"""Tests for the zero-dependency .env loader in testforge.config.

The loader exists because README/.env.example both tell the user to put the LLM
endpoint in `.env` — that promise is only real if something actually reads the
file. These tests pin the three properties that make it safe:

  * shell export  >  .env  >  dataclass default
  * a missing .env is a no-op (CI has none, and mock mode needs no key)
  * an empty .env value must not silently satisfy `mode=api`
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from testforge import config as cfg

MANAGED = (
    "DEEPSEEK_API_KEY",
    "TESTFORGE_MODE",
    "TESTFORGE_MODEL",
    "TESTFORGE_API_BASE",
    "TESTFORGE_EXTRA_BODY",
    "TESTFORGE_MAX_TOKENS",
    "TESTFORGE_CACHE_DIR",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Never let a developer's local .env leak into an assertion about defaults."""
    for key in MANAGED:
        monkeypatch.delenv(key, raising=False)


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_value_present_only_in_file(tmp_path):
    path = write_env(tmp_path, "DEEPSEEK_API_KEY=sk-from-file\n")
    assert cfg._load_dotenv(path) == 1
    assert os.environ["DEEPSEEK_API_KEY"] == "sk-from-file"
    # and from_env() actually consumes it, which is the whole point
    assert cfg.ForgeConfig.from_env().api_key == "sk-from-file"


def test_exported_variable_wins_over_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-shell")
    path = write_env(tmp_path, "DEEPSEEK_API_KEY=sk-from-file\n")
    assert cfg._load_dotenv(path) == 0  # nothing applied: the var already existed
    assert os.environ["DEEPSEEK_API_KEY"] == "sk-from-shell"


def test_empty_file_value_does_not_satisfy_api_mode(tmp_path):
    # An exported-but-empty key must still trip the guidance error rather than
    # sending the agent to the network with a blank credential.
    path = write_env(tmp_path, "DEEPSEEK_API_KEY=\n")
    assert cfg._load_dotenv(path) == 1
    assert os.environ["DEEPSEEK_API_KEY"] == ""
    with pytest.raises(SystemExit) as excinfo:
        cfg.ForgeConfig.from_env(mode="api")
    assert "DEEPSEEK_API_KEY" in str(excinfo.value)


def test_missing_file_is_not_an_error(tmp_path):
    assert cfg._load_dotenv(tmp_path / "absent.env") == 0


def test_comments_blank_and_malformed_lines_are_skipped(tmp_path):
    path = write_env(
        tmp_path,
        "# a comment\n"
        "   \n"
        "   # indented comment\n"
        "NO_EQUALS_HERE\n"
        "=keyless\n"
        "TESTFORGE_MODEL=deepseek-chat\n",
    )
    assert cfg._load_dotenv(path) == 1
    assert os.environ["TESTFORGE_MODEL"] == "deepseek-chat"
    assert "NO_EQUALS_HERE" not in os.environ
    assert "" not in os.environ


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  spaced-value  ", "spaced-value"),
        ('"quoted"', "quoted"),
        ("'single'", "single"),
        ('"unbalanced', '"unbalanced'),  # only one layer of *matching* quotes is removed
        ("keep#hash", "keep#hash"),  # inline comments are deliberately preserved
        ("", ""),
    ],
)
def test_value_normalisation(tmp_path, raw, expected):
    path = write_env(tmp_path, f"TESTFORGE_CACHE_DIR={raw}\n")
    cfg._load_dotenv(path)
    assert os.environ["TESTFORGE_CACHE_DIR"] == expected


def test_project_root_anchors_env_file_not_cwd(tmp_path, monkeypatch):
    """The path must follow the package, so runs from any working directory agree."""
    monkeypatch.chdir(tmp_path)
    assert cfg.ENV_FILE == cfg.PROJECT_ROOT / ".env"
    assert cfg.PROJECT_ROOT in cfg.ENV_FILE.resolve().parents


def test_loader_is_called_at_import_time():
    """`testforge.cli run --mode api` must work with nothing exported, so the
    loader has to run from the module body, not merely exist.

    Asserted structurally (AST) rather than by reloading: reloading re-executes
    `ENV_FILE = PROJECT_ROOT / ".env"`, which wipes any redirected path before
    the loader runs, and asserting on the real repo .env would make the test
    depend on what a given developer happens to have configured locally.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(cfg))
    calls = [
        node
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", None) == "_load_dotenv"
    ]
    assert calls, "config.py 模块顶层缺少 _load_dotenv() 调用：.env 不会被读取，README 的承诺失效"
