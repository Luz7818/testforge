<!-- Rendered from results/exp_api27b_smoke/results.json (in version control): a
     one-cell real-endpoint run (SEU campus gateway, model qwen3.8-27b, 2026-09-29).
     Re-render with:  python - <<'EOF'  (see REPRODUCE.md) or testforge.cli report
     after extracting the row. Token counts are exact; no price was configured
     for this self-hosted endpoint, so no USD figure is claimed. -->

# TestForge report — `numeric.integer_sqrt` (variant B3)

## Headline

| Metric | Value |
|---|---|
| Mutants (total / covered) | 21 / 21 |
| Mutation score (all) | 81.0% |
| Mutation score (covered) | 81.0% |
| Coverage of target (B0 -> B0+suite) | 83.3% -> 100.0% |
| Candidates generated / accepted | 3 / 1 |
| Feedback rounds used | 2 |
| Final suite passes on original | True |
| Wall time | 112s |
| LLM calls / tokens in / out | 2 / 2,480 / 4,096 |
| Estimated cost (USD) | n/a — no price configured for this model; token counts above are exact |

## Gate rejections

| Reason | Count |
|---|---|
| falsifiable | 2 |

## Mutants

| ID | Operator | Line | Killed by B0 | Killed by final | Description |
|---|---|---|---|---|---|
| M001 | ROR | 24 | yes | yes | ROR @ line 24: relational operator Lt -> GtE |
| M002 | CRN | 24 | no | yes | CRN @ line 24: numeric 0 -> 1 |
| M003 | ROR | 26 | yes | yes | ROR @ line 26: relational operator Lt -> GtE |
| M004 | CRN | 26 | no | yes | CRN @ line 26: numeric 2 -> 3 |
| M005 | RTN | 27 | no | yes | RTN @ line 27: return value -> None |
| M006 | CRN | 28 | no | yes | CRN @ line 28: numeric 1 -> 2 |
| M007 | AOR | 28 | no | yes | AOR @ line 28: arithmetic operator Add -> Sub |
| M008 | AOR | 28 | no | no | AOR @ line 28: arithmetic operator FloorDiv -> Div |
| M009 | CRN | 28 | no | no | CRN @ line 28: numeric 2 -> 3 |
| M010 | CRN | 28 | no | no | CRN @ line 28: numeric 1 -> 2 |
| M011 | ROR | 29 | yes | yes | ROR @ line 29: relational operator Lt -> GtE |
| M012 | AOR | 30 | yes | yes | AOR @ line 30: arithmetic operator FloorDiv -> Div |
| M013 | AOR | 30 | yes | yes | AOR @ line 30: arithmetic operator Add -> Sub |
| M014 | AOR | 30 | yes | yes | AOR @ line 30: arithmetic operator Add -> Sub |
| M015 | CRN | 30 | no | no | CRN @ line 30: numeric 1 -> 2 |
| M016 | CRN | 30 | yes | yes | CRN @ line 30: numeric 2 -> 3 |
| M017 | ROR | 31 | yes | yes | ROR @ line 31: relational operator LtE -> Gt |
| M018 | AOR | 31 | yes | yes | AOR @ line 31: arithmetic operator Mult -> Div |
| M019 | AOR | 34 | yes | yes | AOR @ line 34: arithmetic operator Sub -> Add |
| M020 | CRN | 34 | yes | yes | CRN @ line 34: numeric 1 -> 2 |
| M021 | RTN | 35 | yes | yes | RTN @ line 35: return value -> None |

## Accepted tests

### Accepted test file 1

```python
import pytest

from numeric import integer_sqrt


def test_negative_one_raises_valueerror():
    with pytest.raises(ValueError, match="n must be non-negative"):
        integer_sqrt(-1)


def test_large_negative_raises_valueerror():
    with pytest.raises(ValueError):
        integer_sqrt(-10**12)


def test_zero_returns_zero():
    assert integer_sqrt(0) == 0


def test_one_returns_one():
    assert integer_sqrt(1) == 1


def test_two_returns_one():
    assert integer_sqrt(2) == 1


def test_three_returns_one():
    assert integer_sqrt(3) == 1


def test_four_returns_two():
    assert integer_sqrt(4) == 2


def test_negative_zero_not_applicable():
    # In Python, -0 is just 0; ensure 0 is handled
    assert integer_sqrt(0) == 0
```
