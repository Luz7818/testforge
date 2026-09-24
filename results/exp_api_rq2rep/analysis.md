# TestForge experiment analysis

Grid: 10 targets x 3 variants (B0, B2, B5); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 68.2% | 70.8% | 72.4% | 84.5 | 0.00 | 0.0000 |
| B2 | 83.9% | 84.5% | 87.1% | 92.9 | 0.90 | 0.0133 |
| B5 | 91.1% | 93.8% | 91.1% | 97.2 | 1.40 | 0.0547 |

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B2 | 10 | 12,088 | 9,248 |
| B5 | 31 | 36,195 | 40,821 |

## Per-target mutation score (all mutants)

| Target | B0 | B2 | B5 |
|---|---|---|---|
| containers.flatten | 33.3% | 83.3% | 83.3% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% |
| numeric.integer_sqrt | 57.1% | 81.0% | 81.0% |
| parsers.parse_csv_line | 95.8% | 95.8% | 95.8% |
| parsers.parse_kv_pairs | 85.7% | 85.7% | 100.0% |
| string_utils.mask_email | 76.2% | 76.2% | 100.0% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | 91.7% |
| validators.validate_port | 60.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 66.7% | 100.0% |

## Research questions

### RQ5: Does spending the feedback-round budget after zero-acceptance rounds recover surviving mutants?

Paired on 10 targets, B5 minus B2 on MS(all):
- mean uplift: **+7.1%** (median +0.0%, sd 12.3%)
- wins/ties/losses: 3/7/0
- Wilcoxon signed-rank (normal approx, n=3): W+=6.0, z=1.604, p=0.1088
- bootstrap 95% CI of mean uplift: [+0.0%, +15.2%]

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B2 | 3.70 | 0.90 | 0 | 13 | 14 | 0 |
| B5 | 11.30 | 1.40 | 0 | 47 | 45 | 0 |
