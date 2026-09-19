"""Markdown rendering of run results (per-target report + summary tables)."""

from __future__ import annotations

from ..types import VariantResult


def render_target_report(res: VariantResult, cost_summary: dict | None = None) -> str:
    lines: list[str] = []
    lines.append(f"# TestForge report — `{res.target_id}` (variant {res.variant})\n")
    lines.append("## Headline\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Mutants (total / covered) | {res.mutants_total} / {res.mutants_covered} |")
    lines.append(f"| Mutation score (all) | {res.ms_all:.1%} |")
    lines.append(f"| Mutation score (covered) | {res.ms_covered:.1%} |")
    lines.append(
        f"| Coverage of target (B0 -> B0+suite) | {res.b0_coverage_pct:.1f}% -> {res.coverage_pct:.1f}% |"
    )
    lines.append(f"| Candidates generated / accepted | {res.n_generated} / {res.n_accepted} |")
    lines.append(f"| Feedback rounds used | {res.rounds_used} |")
    lines.append(f"| Final suite passes on original | {res.final_suite_passes} |")
    lines.append(f"| Wall time | {res.wall_sec:.0f}s |")
    if cost_summary:
        lines.append(f"| LLM calls / tokens in / out | {cost_summary['calls']} / {cost_summary['tokens_in']} / {cost_summary['tokens_out']} |")
        lines.append(f"| Estimated cost (USD) | {cost_summary['cost_usd']:.4f} |")
    lines.append("")

    if res.rejection_reasons:
        lines.append("## Gate rejections\n")
        lines.append("| Reason | Count |")
        lines.append("|---|---|")
        for reason, n in sorted(res.rejection_reasons.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {reason} | {n} |")
        lines.append("")

    lines.append("## Mutants\n")
    lines.append("| ID | Operator | Line | Killed by B0 | Killed by final | Description |")
    lines.append("|---|---|---|---|---|---|")
    for m in res.mutant_summary:
        lines.append(
            f"| {m['mid']} | {m['operator']} | {m['line']} "
            f"| {'yes' if m['killed_by_b0'] else 'no'} "
            f"| {('yes' if m['killed_by_final'] else 'no') if m['killed_by_final'] is not None else '-'} "
            f"| {m['description'].replace('|', '\\|')} |"
        )
    lines.append("")

    if res.accepted_codes:
        lines.append("## Accepted tests\n")
        for i, code in enumerate(res.accepted_codes, 1):
            lines.append(f"### Accepted test file {i}\n")
            lines.append("```python")
            lines.append(code)
            lines.append("```\n")

    return "\n".join(lines)


def render_summary(rows: list[VariantResult]) -> str:
    lines: list[str] = []
    lines.append("# TestForge summary\n")
    lines.append("| Target | Variant | MS (all) | MS (covered) | Cov % | Gen | Acc | Cost USD |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r.target_id} | {r.variant} | {r.ms_all:.1%} | {r.ms_covered:.1%} "
            f"| {r.coverage_pct:.0f} | {r.n_generated} | {r.n_accepted} | {r.cost_usd:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)
