"""AST mutation operators.

A small, well-defined operator set (the classic ones used in the literature):
AOR (arithmetic operator replacement), ROR (relational operator replacement),
BCR (boolean constant replacement), CRN/CRS (numeric/string constant
replacement), UOR (unary operator removal), RTN (return value mutation).

Deliberate scope decisions:
- one alternate per site (a *selected* operator set) to bound mutant counts;
- annotations and docstrings are never mutated (they are not executable);
- comparison chains (``a < b < c``) are skipped to keep splicing simple.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass


@dataclass
class MutationCandidate:
    node: ast.AST          # the node whose source segment gets replaced
    replacement: str
    operator: str
    description: str


# operator node -> replacement operator node class. Operator tokens carry no
# source positions, so the whole BinOp/Compare expression is re-emitted via
# ast.unparse with the swapped operator (see find_mutation_candidates).
_AOR: dict[type, type] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.FloorDiv: ast.Div,
    ast.Mod: ast.FloorDiv,
    ast.Pow: ast.Mult,
}

_ROR: dict[type, type] = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
    ast.GtE: ast.Lt,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}


def _walk_with_parent(node: ast.AST, parent: ast.AST | None = None, grandparent: ast.AST | None = None):
    yield node, parent, grandparent
    for child in ast.iter_child_nodes(node):
        yield from _walk_with_parent(child, node, parent)


def _is_docstring_constant(node: ast.AST, parent: ast.AST | None, grandparent: ast.AST | None) -> bool:
    """True for the string Constant of a docstring (first statement of a
    module / class / function)."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and isinstance(parent, ast.Expr)
        and grandparent is not None
        and isinstance(grandparent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and bool(grandparent.body)
        and grandparent.body[0] is parent
    )


def _collect_skip_ids(tree: ast.AST) -> set[int]:
    """Nodes that must not be mutated: annotations (not executable at runtime
    in the same way), everything inside them, and *error-message strings*
    inside ``raise`` statements — mutating a message changes no observable
    behavior of the documented contract (the exception type), so such
    mutants are near-equivalent and only add noise."""
    skip: set[int] = set()

    def mark(root: ast.AST) -> None:
        for n in ast.walk(root):
            skip.add(id(n))

    for n in ast.walk(tree):
        if isinstance(n, ast.AnnAssign) and n.annotation is not None:
            mark(n.annotation)
        if isinstance(n, ast.arg) and n.annotation is not None:
            mark(n.annotation)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.returns is not None:
            mark(n.returns)
        if isinstance(n, ast.Raise):
            for m in ast.walk(n):
                if isinstance(m, ast.Constant) and isinstance(m.value, str):
                    skip.add(id(m))
    return skip


def find_mutation_candidates(tree: ast.AST, source: str) -> list[MutationCandidate]:
    skip = _collect_skip_ids(tree)
    cands: list[MutationCandidate] = []

    for node, parent, grandparent in _walk_with_parent(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.BinOp) and type(node.op) in _AOR:
            alt = _AOR[type(node.op)]
            mutated = copy.deepcopy(node)
            mutated.op = alt()
            cands.append(
                MutationCandidate(
                    node,
                    ast.unparse(mutated),
                    "AOR",
                    f"arithmetic operator {type(node.op).__name__} -> {alt.__name__}",
                )
            )
        elif (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and type(node.ops[0]) in _ROR
        ):
            alt = _ROR[type(node.ops[0])]
            mutated = copy.deepcopy(node)
            mutated.ops = [alt()]
            cands.append(
                MutationCandidate(
                    node,
                    ast.unparse(mutated),
                    "ROR",
                    f"relational operator {type(node.ops[0]).__name__} -> {alt.__name__}",
                )
            )
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub, ast.UAdd)):
            seg = ast.get_source_segment(source, node.operand)
            if seg:
                cands.append(
                    MutationCandidate(node, seg, "UOR", f"unary {ast.unparse(node.op)!r} removed")
                )
        elif isinstance(node, ast.Constant):
            if _is_docstring_constant(node, parent, grandparent):
                continue
            v = node.value
            if isinstance(v, bool):
                cands.append(
                    MutationCandidate(node, repr(not v), "BCR", f"boolean {v!r} -> {not v!r}")
                )
            elif isinstance(v, (int, float)):
                cands.append(
                    MutationCandidate(node, repr(v + 1), "CRN", f"numeric {v!r} -> {v + 1!r}")
                )
            elif isinstance(v, str):
                cands.append(
                    MutationCandidate(node, repr(v + "X"), "CRS", f"string {v!r} -> {v + 'X'!r}")
                )
        elif (
            isinstance(node, ast.Return)
            and node.value is not None
            and not (isinstance(node.value, ast.Constant) and node.value.value is None)
        ):
            cands.append(MutationCandidate(node, "return None", "RTN", "return value -> None"))

    return cands
