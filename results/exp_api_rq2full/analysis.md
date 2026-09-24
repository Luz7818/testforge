# TestForge experiment analysis

Grid: 18 targets x 3 variants (B0, B2, B5); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | total cost USD |
|---|---|---|---|---|---|---|
| B0 | 77.2% | 78.1% | 80.0% | 83.1 | 0.00 | 0.0000 |
| B2 | 89.2% | 97.9% | 91.0% | 92.2 | 0.72 | 0.0233 |
| B5 | 93.8% | 100.0% | 93.8% | 95.2 | 1.00 | 0.0690 |

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B2 | 15 | 17,876 | 16,711 |
| B5 | 38 | 44,593 | 51,898 |

## Per-target mutation score (all mutants)

| Target | B0 | B2 | B5 |
|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 33.3% | 66.7% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% |
| date_utils.age_in_days | 100.0% | 100.0% | 100.0% |
| date_utils.days_in_month | 88.9% | 100.0% | 100.0% |
| date_utils.is_leap_year | 82.3% | 82.3% | 100.0% |
| numeric.clamp | 100.0% | 100.0% | 100.0% |
| numeric.integer_sqrt | 57.1% | 81.0% | 81.0% |
| numeric.moving_average | 81.8% | 100.0% | 100.0% |
| parsers.parse_csv_line | 95.8% | 95.8% | 95.8% |
| parsers.parse_kv_pairs | 85.7% | 85.7% | 100.0% |
| parsers.parse_version | 75.0% | 100.0% | 100.0% |
| string_utils.mask_email | 76.2% | 76.2% | 95.2% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 91.7% | 91.7% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 100.0% | 100.0% |

## Research questions

### RQ5: Does spending the feedback-round budget after zero-acceptance rounds recover surviving mutants?

Paired on 18 targets, B5 minus B2 on MS(all):
- mean uplift: **+4.7%** (median +0.0%, sd 9.7%)
- wins/ties/losses: 4/14/0
- Wilcoxon signed-rank (normal approx, n=4): W+=10.0, z=1.826, p=0.0679
- bootstrap 95% CI of mean uplift: [+1.0%, +9.4%]

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B2 | 3.17 | 0.72 | 0 | 16 | 25 | 0 |
| B5 | 7.78 | 1.00 | 0 | 45 | 69 | 0 |
