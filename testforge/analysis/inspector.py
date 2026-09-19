"""Static analysis of the target function via AST inspection.

Everything the generator prompt needs, derived without executing anything:
signature with annotations, docstring, parameter table, function source and
its line range (used later to attribute coverage and mutants to this
function only).
"""

from __future__ import annotations

import ast

from ..types import TargetInfo, TargetSpec


def _unparse_or_none(node) -> str | None:
    return ast.unparse(node) if node is not None else None


def _params_of(node: ast.FunctionDef) -> list[dict]:
    args = node.args
    pos = [*args.posonlyargs, *args.args]
    defaults: list = [*([None] * (len(pos) - len(args.defaults))), *args.defaults]
    params = [
        {
            "name": a.arg,
            "annotation": _unparse_or_none(a.annotation),
            "default": _unparse_or_none(d),
        }
        for a, d in zip(pos, defaults)
    ]
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        params.append(
            {
                "name": a.arg,
                "annotation": _unparse_or_none(a.annotation),
                "default": _unparse_or_none(d),
            }
        )
    if args.vararg:
        params.append({"name": "*" + args.vararg.arg, "annotation": _unparse_or_none(args.vararg.annotation), "default": None})
    if args.kwarg:
        params.append({"name": "**" + args.kwarg.arg, "annotation": _unparse_or_none(args.kwarg.annotation), "default": None})
    return params


def _signature_line(node: ast.FunctionDef) -> str:
    parts = []
    for p in _params_of(node):
        s = p["name"]
        if p["annotation"]:
            s += f": {p['annotation']}"
        if p["default"]:
            s += f" = {p['default']}"
        parts.append(s)
    ret = f" -> {_unparse_or_none(node.returns)}" if node.returns else ""
    return f"def {node.name}({', '.join(parts)}){ret}:"


def inspect_target(spec: TargetSpec) -> TargetInfo:
    source = open(spec.module_path, encoding="utf-8").read()
    tree = ast.parse(source)
    node = None
    for child in ast.walk(tree):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == spec.function_name:
            node = child
            break
    if node is None:
        raise ValueError(
            f"function {spec.function_name!r} not found in {spec.module_path}"
        )
    function_source = ast.get_source_segment(source, node)
    assert function_source is not None
    return TargetInfo(
        spec=spec,
        module_source=source,
        function_source=function_source,
        signature=_signature_line(node),
        docstring=ast.get_docstring(node),
        params=_params_of(node),
        return_annotation=_unparse_or_none(node.returns),
        start_line=node.lineno,
        end_line=node.end_lineno or node.lineno,
    )
