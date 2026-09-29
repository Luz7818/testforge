# Grid comparison: B1 vs B0

- grid A `exp_api27b_full`: n=18 pairs, mean uplift +16.2% (median +13.4%, sd 17.0%)
- grid B `exp_api27b_replicate`: n=18 pairs, mean uplift +13.6% (median +13.4%, sd 12.3%)
- pooled: n=36 pairs, mean uplift **+14.9%** (median +13.4%, sd 14.7%)
- pooled wins/ties/losses: 25/11/0
- pooled Wilcoxon signed-rank (normal approx): W+=325.0, z=4.378, p=0.0
- pooled bootstrap 95% CI: [+10.4%, +19.8%]

- consistency check B3 vs B1: grid A mean +0.0%, grid B mean +0.3%, pooled n=36 (35 ties / 36)
- consistency check B2 vs B1: grid A mean +0.0%, grid B mean +0.0%, pooled n=36 (36 ties / 36)