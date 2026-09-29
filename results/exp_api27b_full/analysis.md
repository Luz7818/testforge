# TestForge experiment analysis

Grid: 18 targets x 5 variants (B0, B1, B2, B3, B4); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | USD total (priced runs only) |
|---|---|---|---|---|---|---|
| B0 | 77.6% | 80.6% | 80.1% | 83.1 | 0.00 | — |
| B1 | 93.8% | 100.0% | 94.2% | 94.0 | 1.78 | — |
| B2 | 93.8% | 100.0% | 94.2% | 94.0 | 0.78 | — |
| B3 | 93.8% | 100.0% | 94.2% | 94.0 | 0.78 | — |
| B4 | 93.8% | 100.0% | 94.2% | 94.0 | 0.78 | — |

The USD column only sums cells whose run carried an explicit price source (TESTFORGE_PRICE_* env or a pricing.json entry; see the price source in the per-cell ledger). Legacy archives priced with undocumented placeholder rates count as unpriced here — their exact token totals are in `LLM usage per variant` below.

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B1 | 15 | 18,945 | 26,319 |
| B2 | 15 | 18,945 | 26,319 |
| B3 | 18 | 22,393 | 34,560 |
| B4 | 18 | 22,191 | 32,793 |

## Per-target mutation score (all mutants)

| Target | B0 | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 100.0% | 100.0% | 100.0% | 100.0% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% | 71.4% | 71.4% |
| date_utils.age_in_days | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_utils.days_in_month | 88.9% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_utils.is_leap_year | 87.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| numeric.clamp | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| numeric.integer_sqrt | 56.2% | 87.5% | 87.5% | 87.5% | 87.5% |
| numeric.moving_average | 81.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_csv_line | 93.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_kv_pairs | 85.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_version | 75.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| string_utils.mask_email | 81.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 66.7% | 66.7% | 66.7% | 66.7% |

## Per-target uplift (B1 minus B0), sorted

| Target | B0 | B1 | uplift |
|---|---|---|---|
| containers.flatten | 33.3% | 100.0% | +66.7% |
| validators.validate_port | 60.0% | 100.0% | +40.0% |
| numeric.integer_sqrt | 56.2% | 87.5% | +31.2% |
| parsers.parse_version | 75.0% | 100.0% | +25.0% |
| containers.chunk | 80.0% | 100.0% | +20.0% |
| string_utils.mask_email | 81.2% | 100.0% | +18.8% |
| numeric.moving_average | 81.8% | 100.0% | +18.2% |
| containers.most_frequent | 57.1% | 71.4% | +14.3% |
| parsers.parse_kv_pairs | 85.7% | 100.0% | +14.3% |
| date_utils.is_leap_year | 87.5% | 100.0% | +12.5% |
| string_utils.slugify | 75.0% | 87.5% | +12.5% |
| date_utils.days_in_month | 88.9% | 100.0% | +11.1% |
| parsers.parse_csv_line | 93.8% | 100.0% | +6.2% |
| date_utils.age_in_days | 100.0% | 100.0% | +0.0% |
| numeric.clamp | 100.0% | 100.0% | +0.0% |
| string_utils.truncate_with_ellipsis | 75.0% | 75.0% | +0.0% |
| validators.normalize_hex_color | 100.0% | 100.0% | +0.0% |
| validators.validate_username | 66.7% | 66.7% | +0.0% |

## Research questions

### RQ1: Can single-shot LLM tests improve fault detection beyond the existing suite?

Paired on 18 targets, B1 minus B0 on MS(all):
- mean uplift: **+16.2%** (median +13.4%, sd 17.0%)
- wins/ties/losses: 13/5/0
- Wilcoxon signed-rank (normal approx, n=13): W+=91.0, z=3.182, p=0.0015
- bootstrap 95% CI of mean uplift: [+9.2%, +24.5%]

### RQ2: Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?

Paired on 18 targets, B3 minus B1 on MS(all):
- mean uplift: **+0.0%** (median +0.0%, sd 0.0%)
- wins/ties/losses: 0/18/0
- no non-zero paired differences (treatment changed no target); significance test not applicable

LLM usage of B3: 18 calls, 22,393 input / 34,560 output tokens over 18 targets — token counts are exact.
No price was configured for this run, so no USD figure is derived; the token counts above are the cost accounting.

### RQ3: What does the quality gate contribute on its own (reliability vs raw generation)?

Paired on 18 targets, B2 minus B1 on MS(all):
- mean uplift: **+0.0%** (median +0.0%, sd 0.0%)
- wins/ties/losses: 0/18/0
- no non-zero paired differences (treatment changed no target); significance test not applicable

### RQ4: Ablation: mutant-survivor feedback vs coverage-gap feedback.

Paired on 18 targets, B4 minus B3 on MS(all):
- mean uplift: **+0.0%** (median +0.0%, sd 0.0%)
- wins/ties/losses: 0/18/0
- no non-zero paired differences (treatment changed no target); significance test not applicable

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B1 | 2.50 | 1.78 | 0 | 0 | 13 | 0 |
| B2 | 2.50 | 0.78 | 0 | 18 | 13 | 0 |
| B3 | 3.00 | 0.78 | 0 | 27 | 13 | 0 |
| B4 | 3.00 | 0.78 | 0 | 27 | 13 | 0 |

## Cross-model comparison: qwen3.8-27b vs qwen3-vl-8b

Grids paired on the (target, variant) cells present in both; grid A = qwen3.8-27b (this analysis), grid B = qwen3-vl-8b.

| Variant | mean MS(all) A | mean MS(all) B | Δ (B − A) |
|---|---|---|---|
| B0 | 77.6% | 77.6% | +0.0% |
| B1 | 93.8% | 91.3% | -2.5% |
| B2 | 93.8% | 91.3% | -2.5% |
| B3 | 93.8% | 91.3% | -2.5% |
| B4 | 93.8% | 91.3% | -2.5% |

### Generation uplift per grid (RQ1, B1 − B0)

- **qwen3.8-27b — B1 vs B0**: mean uplift +16.2% (median +13.4%); 13/5/0 win/tie/loss; Wilcoxon p=0.0015, bootstrap 95% CI [+9.2%, +24.5%] (n=18)
- **qwen3-vl-8b — B1 vs B0**: mean uplift +13.6% (median +12.5%); 11/7/0 win/tie/loss; Wilcoxon p=0.0033, bootstrap 95% CI [+7.8%, +19.7%] (n=18)

### Gate contribution per grid (RQ3, accepted tests/target)

| Grid | B1 accepted/target | B2 accepted/target | ratio B2/B1 |
|---|---|---|---|
| qwen3.8-27b | 1.78 | 0.78 | 0.44 |
| qwen3-vl-8b | 1.28 | 0.61 | 0.48 |

### LLM token totals per grid

| Grid | tokens in | tokens out |
|---|---|---|
| qwen3.8-27b | 82,474 | 119,991 |
| qwen3-vl-8b | 79,896 | 76,106 |
