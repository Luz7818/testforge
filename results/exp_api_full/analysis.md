# TestForge experiment analysis

Grid: 18 targets x 5 variants (B0, B1, B2, B3, B4); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 77.6% | 80.6% | 80.1% | 83.1 | 0.00 | 0.0000 |
| B1 | 91.3% | 100.0% | 93.1% | 92.6 | 1.28 | 0.0233 |
| B2 | 91.3% | 100.0% | 93.1% | 92.6 | 0.61 | 0.0233 |
| B3 | 91.3% | 100.0% | 93.1% | 92.6 | 0.61 | 0.0292 |
| B4 | 91.3% | 100.0% | 93.1% | 92.6 | 0.61 | 0.0293 |

## Per-target mutation score (all mutants)

| Target | B0 | B1 | B2 | B3 | B4 |
|---|---|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 66.7% | 66.7% | 66.7% | 66.7% |
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
| string_utils.slugify | 75.0% | 87.5% | 87.5% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 100.0% | 100.0% | 100.0% | 100.0% |

## Research questions

### RQ1: Can single-shot LLM tests improve fault detection beyond the existing suite?

Paired on 18 targets, B1 minus B0 on MS(all):
- mean uplift: **+13.6%** (median +12.5%, sd 13.5%)
- wins/ties/losses: 11/7/0
- Wilcoxon signed-rank (normal approx, n=11): W+=66.0, z=2.937, p=0.0033
- bootstrap 95% CI of mean uplift: [+7.8%, +19.7%]

### RQ2: Does the mutation-feedback loop add fault detection over single-shot generation, and at what cost?

Paired on 18 targets, B3 minus B1 on MS(all):
- mean uplift: **+0.0%** (median +0.0%, sd 0.0%)
- wins/ties/losses: 0/18/0
- no non-zero paired differences (treatment changed no target); significance test not applicable

Cost of B3: total $0.0292 over 18 targets (mean $0.0016/target; token counts are exact in the ledger, price is configurable).

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
| B1 | 2.17 | 1.28 | 0 | 0 | 12 | 0 |
| B2 | 2.17 | 0.61 | 0 | 12 | 12 | 0 |
| B3 | 2.83 | 0.61 | 0 | 18 | 18 | 0 |
| B4 | 2.83 | 0.61 | 0 | 19 | 17 | 0 |
