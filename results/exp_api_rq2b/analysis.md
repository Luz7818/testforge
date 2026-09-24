# TestForge experiment analysis

Grid: 10 targets x 3 variants (B0, B2, B5); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 68.2% | 70.8% | 72.4% | 84.5 | 0.00 | 0.0000 |
| B2 | 82.3% | 86.6% | 85.5% | 92.8 | 0.80 | 0.0137 |
| B5 | 88.9% | 93.5% | 88.9% | 98.1 | 1.20 | 0.0566 |

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B2 | 10 | 12,088 | 9,411 |
| B5 | 32 | 37,775 | 42,317 |

## Per-target mutation score (all mutants)

| Target | B0 | B2 | B5 |
|---|---|---|---|
| containers.flatten | 33.3% | 33.3% | 66.7% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% |
| numeric.integer_sqrt | 57.1% | 81.0% | 81.0% |
| parsers.parse_csv_line | 95.8% | 95.8% | 95.8% |
| parsers.parse_kv_pairs | 85.7% | 85.7% | 100.0% |
| string_utils.mask_email | 76.2% | 76.2% | 95.2% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | 91.7% |
| validators.validate_port | 60.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 100.0% | 100.0% |

## Research questions

### RQ5: Does spending the feedback-round budget after zero-acceptance rounds recover surviving mutants?

Paired on 10 targets, B5 minus B2 on MS(all):
- mean uplift: **+6.7%** (median +0.0%, sd 11.7%)
- wins/ties/losses: 3/7/0
- Wilcoxon signed-rank (normal approx, n=3): W+=6.0, z=1.604, p=0.1088
- bootstrap 95% CI of mean uplift: [+0.0%, +13.8%]

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B2 | 4.00 | 0.80 | 0 | 11 | 19 | 0 |
| B5 | 11.90 | 1.20 | 0 | 37 | 63 | 0 |
