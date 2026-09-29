# TestForge experiment analysis

Grid: 1 targets x 1 variants (B3); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | USD total (priced runs only) |
|---|---|---|---|---|---|---|
| B3 | 81.0% | 81.0% | 81.0% | 100.0 | 1.00 | — |

The USD column only sums cells whose run carried an explicit price source (TESTFORGE_PRICE_* env or a pricing.json entry; see the price source in the per-cell ledger). Legacy archives priced with undocumented placeholder rates count as unpriced here — their exact token totals are in `LLM usage per variant` below.

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B3 | 2 | 2,480 | 4,096 |

## Per-target mutation score (all mutants)

| Target | B3 |
|---|---|
| numeric.integer_sqrt | 81.0% |

## Research questions

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B3 | 3.00 | 1.00 | 0 | 2 | 0 | 0 |

## Cross-model comparison: qwen3.8-27b vs qwen3-vl-8b

Grids paired on the (target, variant) cells present in both; grid A = qwen3.8-27b (this analysis), grid B = qwen3-vl-8b.

| Variant | mean MS(all) A | mean MS(all) B | Δ (B − A) |
|---|---|---|---|
| B3 | 81.0% | 91.3% | +10.3% |

### Generation uplift per grid (RQ1, B1 − B0)

- **qwen3-vl-8b — B1 vs B0**: mean uplift +13.6% (median +12.5%); 11/7/0 win/tie/loss; Wilcoxon p=0.0033, bootstrap 95% CI [+7.8%, +19.7%] (n=18)

### Gate contribution per grid (RQ3, accepted tests/target)

| Grid | B1 accepted/target | B2 accepted/target | ratio B2/B1 |
|---|---|---|---|
| qwen3-vl-8b | 1.28 | 0.61 | 0.48 |

### LLM token totals per grid

| Grid | tokens in | tokens out |
|---|---|---|
| qwen3.8-27b | 2,480 | 4,096 |
| qwen3-vl-8b | 79,896 | 76,106 |
