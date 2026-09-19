"""Mutant generation: candidate discovery, source splicing, validation,
stratified sampling, stable identifiers."""

from __future__ import annotations

import ast
import random
from collections import defaultdict

from ..types import Mutant
from ..utils import mini_diff
from .operators import MutationCandidate, find_mutation_candidates


def _char_offset(lines: list[str], lineno: int, col_bytes: int) -> int:
    """Convert ast's (1-based lineno, byte-offset col) into a char offset in
    the whole source string (robust for non-ASCII sources)."""
    prefix = "".join(lines[: lineno - 1])
    line_text = lines[lineno - 1] if lineno - 1 < len(lines) else ""
    prefix += line_text.encode("utf-8")[:col_bytes].decode("utf-8", errors="replace")
    return len(prefix)


def splice(source: str, node: ast.AST, replacement: str) -> str:
    lines = source.splitlines(keepends=True)
    start = _char_offset(lines, node.lineno, node.col_offset)
    end = _char_offset(lines, node.end_lineno, node.end_col_offset)  # type: ignore[arg-type]
    return source[:start] + replacement + source[end:]


def _stratified_sample(items: list, k: int, seed: int) -> list:
    """Keep operator diversity when capping mutant counts: round-robin across
    operator groups (each internally shuffled with the run seed)."""
    rng = random.Random(seed)
    groups: dict[str, list] = defaultdict(list)
    for item in items:
        groups[item[0].operator].append(item)
    for g in groups.values():
        rng.shuffle(g)
    picked: list = []
    groups_list = list(groups.values())
    while len(picked) < k and groups_list:
        for g in list(groups_list):
            if not g:
                groups_list.remove(g)
                continue
            picked.append(g.pop(0))
            if len(picked) >= k:
                break
    return picked


def generate_mutants(
    module_source: str,
    function_name: str | None = None,
    max_mutants: int = 24,
    seed: int = 0,
) -> list[Mutant]:
    tree = ast.parse(module_source)
    root = tree
    if function_name is not None:
        root = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                root = node
                break
        if root is None:
            raise ValueError(f"function {function_name!r} not found in module source")

    candidates: list[MutationCandidate] = find_mutation_candidates(root, module_source)

    built: list[tuple[MutationCandidate, str]] = []
    seen: set[tuple] = set()
    for c in candidates:
        try:
            mutated = splice(module_source, c.node, c.replacement)
            ast.parse(mutated)  # a mutant that cannot parse is discarded
        except (SyntaxError, ValueError, IndentationError, RecursionError):
            continue
        key = (c.node.lineno, c.node.col_offset, c.replacement)
        if key in seen:
            continue
        seen.add(key)
        built.append((c, mutated))

    if len(built) > max_mutants:
        built = _stratified_sample(built, max_mutants, seed)

    built.sort(key=lambda t: (t[0].node.lineno, t[0].node.col_offset))

    mutants: list[Mutant] = []
    for i, (c, mutated) in enumerate(built, start=1):
        original_seg = ast.get_source_segment(module_source, c.node) or ""
        mutants.append(
            Mutant(
                mid=f"M{i:03d}",
                operator=c.operator,
                description=f"{c.operator} @ line {c.node.lineno}: {c.description}",
                line=c.node.lineno,
                original=original_seg,
                replacement=c.replacement,
                mutated_source=mutated,
                diff=mini_diff(module_source, mutated),
            )
        )
    return mutants
