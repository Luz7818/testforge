# Reproducing the published results

Everything numbered in [README.md](README.md) and [docs/report.md](docs/report.md)
comes from grids archived under `results/exp_*`. This file turns "trust me" into
"run it yourself": four steps from a fresh clone to the published numbers, no
network needed for the offline path.

Two levels of reproduction are claimed, and they mean different things:

| Level | What repeats | What may differ |
|---|---|---|
| **Mock grid (offline)** | JSON output is bit-identical across runs | only `wall_sec` |
| **Real-LLM grid** | the *statistics*: direction, significance, effect size class | exact per-cell scores (LLM sampling) |

## Step 1 — clone and install

```bash
git clone https://github.com/Luz7818/testforge.git
cd testforge
pip install -e .[dev]
```

`[dev]` includes `pyflakes`, so both repo gates work on a fresh machine:

```bash
python -m pytest              # 89 tests
python -m pyflakes testforge experiments tests
```

## Step 2 — run the published grid (offline, zero cost)

The published 90-cell grids (`results/exp_api27b_full`, `exp_api27b_replicate`
for the real model, `exp_mock_full` for the offline mock) were NOT run with the
code defaults (24 mutants / 4 candidates / 3 rounds). They used **16 mutants /
target, 3 candidates / round, 2 feedback rounds, gate reruns ×3**. That parameter set is pinned as a preset, so you don't
have to remember it:

```bash
python experiments/run_experiment.py --mode mock --preset published --out results/exp_mock_published_repro
```

The runner echoes the effective parameters on the first line; if you use any
other flags, that line is what your run actually did.

## Step 3 — check the fingerprints against the archive

```bash
python - <<'EOF'
import json
def fp(path):
    rows = json.loads(open(path, encoding="utf-8").read())
    ok = [r for r in rows if "error" not in r]
    return (max(r["mutants_total"] for r in ok),
            max(r["n_generated"] for r in ok),
            max(r["rounds_used"] for r in ok),
            len(rows))
arch = fp("results/exp_mock_full/results.json")
mine = fp("results/exp_mock_published_repro/results.json")
print("archive:", arch)
print("mine:   ", mine)
assert arch == mine == (16, 6, 2, 90), "fingerprint mismatch"
print("fingerprint OK: 16 mutants, max 6 generated (3 x 2 rounds), 90 cells")
EOF
```

## Step 4 — analyze and compare the numbers

```bash
python experiments/analyze.py --exp results/repro_mock_published
python experiments/plots.py   --exp results/repro_mock_published --label "mock repro"
```

Expected (from `results/exp_mock_full/analysis.md`, committed):

| Variant | mean MS(all) | median | mean tests accepted |
|---|---|---|---|
| B0 | 77.6% | 80.6% | — |
| B1 | 85.5% | 90.3% | 2.50 |
| B2/B3/B4 | 85.5% | 90.3% | 0.56 |

And RQ1 (B1 − B0, paired on 18 targets): mean uplift **+7.8pp**, 9 wins / 9 ties
/ 0 losses, Wilcoxon p = 0.0076, bootstrap 95% CI [+4.0, +11.8].

The published *real-LLM* grids are reproduced the same way: the archived
`results/exp_api27b_full` and `exp_api27b_replicate` (two independent samplings
on qwen3.8-27B) carry the same fingerprint, and their pooled RQ1 is in
`results/exp_api27b_full/compare.md` (+14.9pp, p<0.0001).

For a single-cell sanity check (~1 min, offline):

```bash
python -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock
# expected: MS(all) = 76.2%  gen=8  acc=2  (defaults: 24 mutants; the published
# grid value for the same target at 16 mutants is 75.0% — different cap, different sample)
```

## Reproducing the real-LLM grids

Requires any OpenAI-compatible endpoint (see `.env.example`; the published
grids used the SEU campus gateway serving qwen3.8-27B with thinking disabled —
if your gateway WAF-blocks the openai SDK, set `TESTFORGE_TRANSPORT=urllib`):

```bash
export TESTFORGE_CACHE_DIR=llm_cache_repro   # fresh dir = independent sampling
python experiments/run_experiment.py --mode api --preset published --out results/repro_api_published
python experiments/analyze.py --exp results/repro_api_published
python experiments/compare_grids.py --a results/exp_api27b_full --b results/repro_api_published --treat B1 --base B0
```

Expectation: not bit-identical (fresh sampling), but the published *claims*
should re-appear: B1 > B0 with Wilcoxon p < 0.05, gate (B2) cutting accepted
tests to roughly 40-44% of B1 at equal mutation score. If your endpoint serves
a different model, treat it as a new experiment — the model-capability history
(8B vs 27B) is in `docs/report.md` §6.8.

## About cost numbers

Token counts in every ledger are exact. USD figures appear **only** when a price
was explicitly configured for the run (`pricing.json` entry with source and
effective date, or `TESTFORGE_PRICE_*` env) and are annotated with that source.
Archived grids from v0.1 were priced with undocumented placeholder rates; they
are reported as unpriced (token counts only). The prompt cache (`llm_cache/`,
git-ignored) may be deleted at any time — replays then re-hit the endpoint;
nothing else changes.
