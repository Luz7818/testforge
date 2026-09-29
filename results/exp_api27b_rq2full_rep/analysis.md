# TestForge experiment analysis

Grid: 18 targets x 3 variants (B0, B2, B5); 0 cell(s) errored.

## Aggregate results

| Variant | mean MS(all) | median | mean MS(covered) | mean cov % | mean tests accepted | USD total (priced runs only) |
|---|---|---|---|---|---|---|
| B0 | 77.2% | 78.1% | 80.0% | 83.1 | 0.00 | — |
| B2 | 92.3% | 100.0% | 92.6% | 94.0 | 0.78 | — |
| B5 | 95.5% | 100.0% | 95.5% | 96.7 | 0.89 | — |

The USD column only sums cells whose run carried an explicit price source (TESTFORGE_PRICE_* env or a pricing.json entry; see the price source in the per-cell ledger). Legacy archives priced with undocumented placeholder rates count as unpriced here — their exact token totals are in `LLM usage per variant` below.

## LLM usage per variant

| Variant | LLM calls | tokens in | tokens out |
|---|---|---|---|
| B2 | 15 | 18,945 | 34,950 |
| B5 | 32 | 39,211 | 85,764 |

## Per-target mutation score (all mutants)

| Target | B0 | B2 | B5 |
|---|---|---|---|
| containers.chunk | 80.0% | 100.0% | 100.0% |
| containers.flatten | 33.3% | 83.3% | 83.3% |
| containers.most_frequent | 57.1% | 71.4% | 71.4% |
| date_utils.age_in_days | 100.0% | 100.0% | 100.0% |
| date_utils.days_in_month | 88.9% | 100.0% | 100.0% |
| date_utils.is_leap_year | 82.3% | 100.0% | 100.0% |
| numeric.clamp | 100.0% | 100.0% | 100.0% |
| numeric.integer_sqrt | 57.1% | 81.0% | 81.0% |
| numeric.moving_average | 81.8% | 100.0% | 100.0% |
| parsers.parse_csv_line | 95.8% | 95.8% | 95.8% |
| parsers.parse_kv_pairs | 85.7% | 100.0% | 100.0% |
| parsers.parse_version | 75.0% | 100.0% | 100.0% |
| string_utils.mask_email | 76.2% | 100.0% | 100.0% |
| string_utils.slugify | 75.0% | 87.5% | 87.5% |
| string_utils.truncate_with_ellipsis | 75.0% | 75.0% | 100.0% |
| validators.normalize_hex_color | 100.0% | 100.0% | 100.0% |
| validators.validate_port | 60.0% | 100.0% | 100.0% |
| validators.validate_username | 66.7% | 66.7% | 100.0% |

## Research questions

### RQ5: Does spending the feedback-round budget after zero-acceptance rounds recover surviving mutants?

Paired on 18 targets, B5 minus B2 on MS(all):
- mean uplift: **+3.2%** (median +0.0%, sd 9.5%)
- wins/ties/losses: 2/16/0
- Wilcoxon signed-rank (normal approx, n=2): W+=3.0, z=1.342, p=0.1797
- bootstrap 95% CI of mean uplift: [+0.0%, +8.3%]

## Gate behaviour (generation variants)

| Variant | generated | accepted | flaky rejects | falsifiable rejects | failing rejects | timeout rejects |
|---|---|---|---|---|---|---|
| B2 | 3.17 | 0.78 | 0 | 24 | 15 | 0 |
| B5 | 6.94 | 0.89 | 0 | 60 | 45 | 0 |
