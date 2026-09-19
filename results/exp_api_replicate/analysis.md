# TestForge experiment analysis

Grid: 18 targets x 5 variants (B0, B1, B2, B3, B4); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 77.6% | 80.6% | 80.1% | 83.1 | 0.00 | 0.0000 |
| B1 | 89.4% | 92.7% | 90.9% | 92.7 | 1.06 | 0.0235 |
| B2 | 89.4% | 92.7% | 90.9% | 92.7 | 0.61 | 0.0235 |
| B3 | 90.6% | 96.9% | 92.0% | 92.7 | 0.67 | 0.0315 |
| B4 | 90.6% | 96.9% | 92.0% | 92.7 | 0.67 | 0.0304 |

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B1 | 15 | 17,876 | 16,842 |
| B2 | 15 | 17,876 | 16,842 |
| B3 | 20 | 23,412 | 22,711 |
| B4 | 20 | 23,080 | 21,924 |

## Per-target mutation score (all mutants)

| Target | B0 | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 83.3% | 83.3% | 83.3% | 83.3% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% | 71.4% | 71.4% |
| date_utils.age_in_days | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_utils.days_in_month | 88.9% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_utils.is_leap_year | 87.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| numeric.clamp | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| numeric.integer_sqrt | 56.2% | 81.2% | 81.2% | 81.2% | 81.2% |
| numeric.moving_average | 81.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_csv_line | 93.8% | 93.8% | 93.8% | 93.8% | 93.8% |
| parsers.parse_kv_pairs | 85.7% | 85.7% | 85.7% | 85.7% | 85.7% |
| parsers.parse_version | 75.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| string_utils.mask_email | 81.2% | 81.2% | 81.2% | 81.2% | 81.2% |
| string_utils.slugify | 75.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | 91.7% | 91.7% | 91.7% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 80.0% | 80.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 66.7% | 66.7% | 66.7% | 66.7% |

## Per-target uplift (B1 minus B0), sorted

| Target | B0 | B1 | uplift |
|---|---|---|---|
| containers.flatten | 33.3% | 83.3% | +50.0% |
| numeric.integer_sqrt | 56.2% | 81.2% | +25.0% |
| parsers.parse_version | 75.0% | 100.0% | +25.0% |
| validators.validate_port | 60.0% | 80.0% | +20.0% |
| containers.chunk | 80.0% | 100.0% | +20.0% |
| numeric.moving_average | 81.8% | 100.0% | +18.2% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | +16.7% |
| containers.most_frequent | 57.1% | 71.4% | +14.3% |
| date_utils.is_leap_year | 87.5% | 100.0% | +12.5% |
| date_utils.days_in_month | 88.9% | 100.0% | +11.1% |
| date_utils.age_in_days | 100.0% | 100.0% | +0.0% |
| numeric.clamp | 100.0% | 100.0% | +0.0% |
| parsers.parse_csv_line | 93.8% | 93.8% | +0.0% |
| parsers.parse_kv_pairs | 85.7% | 85.7% | +0.0% |
| string_utils.mask_email | 81.2% | 81.2% | +0.0% |
| string_utils.slugify | 75.0% | 75.0% | +0.0% |
| validators.normalize_hex_color | 100.0% | 100.0% | +0.0% |
| validators.validate_username | 66.7% | 66.7% | +0.0% |

## Research questions

### RQ1: Can single-shot LLM tests improve fault detection beyond the existing suite?

Paired on 18 targets, B1 minus B0 on MS(all):
- mean uplift: **+11.8%** (median +11.8%, sd 13.6%)
- wins/ties/losses: 10/8/0
- Wilcoxon signed-rank (normal approx, n=10): W+=55.0, z=2.805, p=0.005
- bootstrap 95% CI of mean uplift: [+6.2%, +18.3%]

### RQ2: Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?

Paired on 18 targets, B3 minus B1 on MS(all):
- mean uplift: **+1.1%** (median +0.0%, sd 4.7%)
- wins/ties/losses: 1/17/0
- Wilcoxon signed-rank (normal approx, n=1): W+=1.0, z=1.0, p=0.3173
- bootstrap 95% CI of mean uplift: [+0.0%, +3.3%]

Cost of B3: total $0.0315 over 18 targets (mean $0.0018/target; token counts are exact in the ledger, price is configurable).

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
| B1 | 2.28 | 1.06 | 0 | 0 | 21 | 0 |
| B2 | 2.28 | 0.61 | 0 | 8 | 21 | 0 |
| B3 | 3.06 | 0.67 | 0 | 15 | 27 | 0 |
| B4 | 3.11 | 0.67 | 0 | 17 | 26 | 0 |
