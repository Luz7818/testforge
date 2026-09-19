# TestForge experiment analysis

Grid: 18 targets x 5 variants (B0, B1, B2, B3, B4); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 77.6% | 80.6% | 80.1% | 83.1 | 0.00 | 0.0000 |
| B1 | 85.5% | 90.3% | 86.1% | 91.5 | 2.50 | 0.0000 |
| B2 | 85.5% | 90.3% | 86.1% | 87.2 | 0.56 | 0.0000 |
| B3 | 85.5% | 90.3% | 86.1% | 87.2 | 0.56 | 0.0000 |
| B4 | 85.5% | 90.3% | 86.1% | 87.2 | 0.56 | 0.0000 |

## Per-target mutation score (all mutants)

| Target | B0 | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 33.3% | 33.3% | 33.3% | 33.3% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% | 71.4% | 71.4% |
| date_utils.age_in_days | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_utils.days_in_month | 88.9% | 88.9% | 88.9% | 88.9% | 88.9% |
| date_utils.is_leap_year | 87.5% | 93.8% | 93.8% | 93.8% | 93.8% |
| numeric.clamp | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| numeric.integer_sqrt | 56.2% | 75.0% | 75.0% | 75.0% | 75.0% |
| numeric.moving_average | 81.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_csv_line | 93.8% | 93.8% | 93.8% | 93.8% | 93.8% |
| parsers.parse_kv_pairs | 85.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| parsers.parse_version | 75.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| string_utils.mask_email | 81.2% | 81.2% | 81.2% | 81.2% | 81.2% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | 91.7% | 91.7% | 91.7% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 80.0% | 80.0% | 80.0% | 80.0% |
| validators.validate_username | 66.7% | 66.7% | 66.7% | 66.7% | 66.7% |

## Research questions

### RQ1: Can single-shot LLM tests improve fault detection beyond the existing suite?

Paired on 18 targets, B1 minus B0 on MS(all):
- mean uplift: **+7.8%** (median +3.1%, sd 8.6%)
- wins/ties/losses: 9/9/0
- Wilcoxon signed-rank (normal approx, n=9): W+=45.0, z=2.668, p=0.0076
- bootstrap 95% CI of mean uplift: [+4.0%, +11.8%]

### RQ2: Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?

Paired on 18 targets, B3 minus B1 on MS(all):
- mean uplift: **+0.0%** (median +0.0%, sd 0.0%)
- wins/ties/losses: 0/18/0
- no non-zero paired differences (treatment changed no target); significance test not applicable

Cost of B3: total $0.0000 over 18 targets (mean $0.0000/target; token counts are exact in the ledger, price is configurable).

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
| B1 | 2.50 | 2.50 | 0 | 0 | 0 | 0 |
| B2 | 2.50 | 0.56 | 0 | 35 | 0 | 0 |
| B3 | 3.50 | 0.56 | 0 | 53 | 0 | 0 |
| B4 | 3.50 | 0.56 | 0 | 53 | 0 | 0 |
