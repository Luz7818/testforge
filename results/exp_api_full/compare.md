# Grid comparison: B1 vs B0

- grid A `exp_api_full`: n=18 pairs, mean uplift +13.6% (median +12.5%, sd 13.5%)
- grid B `exp_api_replicate`: n=18 pairs, mean uplift +11.8% (median +11.8%, sd 13.6%)
- pooled: n=36 pairs, mean uplift **+12.7%** (median +12.5%, sd 13.4%)
- pooled wins/ties/losses: 21/15/0
- pooled Wilcoxon signed-rank (normal approx): W+=231.0, z=4.02, p=0.0001
- pooled bootstrap 95% CI: [+8.5%, +17.2%]

- consistency check B3 vs B1: grid A mean +0.0%, grid B mean +1.1%, pooled n=36 (35 ties / 36)
- consistency check B2 vs B1: grid A mean +0.0%, grid B mean +0.0%, pooled n=36 (36 ties / 36)