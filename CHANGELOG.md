# Changelog

All notable changes to TestForge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/): breaking the documented CLI/config contract
bumps the major, added capability the minor, fixes the patch.

## [0.3.0] — 2026-09-30

The external-validity release: a second, larger model reruns the same grids
under the same protocol, and the backend learns to survive the campus
gateway that served them.

### Added

- External validity (docs/report.md §6.8): **qwen3.8-27B** (SEU campus
  OpenAI-compatible gateway) reruns the published protocols — the B0–B4 grid
  with `--preset published` (90 cells) and the B5 grid with
  `--preset published-b5` (54 cells) — **144 cells, zero errors**.
  RQ1 replicates stronger (+16.2pp, p=0.0015; 8B: +13.6pp) and the gate
  result replicates (1.78 → 0.78 accepted tests/target at equal MS, ratio
  0.44); the feedback-loop gain **decays with model capability** (B5−B2:
  +2.6pp, 3 wins / 15 ties / **0 losses**, p=0.109, vs 8B's +4.7pp / pooled
  +4.2pp), with both models converging to the same ~93-94% ceiling under the
  24-mutant protocol. Grids, analyses and cross-model comparison sections are
  committed under `results/exp_api27b_full/` and `results/exp_api27b_rq2full/`.
- `experiments/analyze.py --compare-with <exp_dir>`: cross-model comparison
  section (per-variant MS, RQ1 stats per grid, gate ratio, token totals).
- `TESTFORGE_TRANSPORT=urllib`: a stdlib HTTP transport for the
  OpenAI-compatible backend, alongside the default SDK transport. Some campus
  gateways WAF-block the SDK's HTTP stack with an HTML "access denied"
  interstitial while serving plain requests fine (verified against
  openapi.seu.edu.cn: curl and urllib pass, the SDK transport is rejected);
  the urllib transport uses the identical wire format and gets through.
- `TESTFORGE_MIN_CALL_INTERVAL_SEC` (gap between real API calls) and
  `TESTFORGE_LLM_RETRIES` (retry budget), for gateways that answer request
  bursts with HTTP 420 throttling. Completed cells are crash-safe: rerunning
  the same grid command retries only errored cells.
- CI `api-smoke` opt-in: the manual job now also requires a
  `TESTFORGE_SMOKE_ENABLED=1` secret, because an endpoint that is only
  reachable from campus cannot smoke-test from public runners (it would fail
  on every dispatch instead of skipping green).

### Fixed

- The prompt-cache key now includes `TESTFORGE_EXTRA_BODY`: it can flip
  provider-side behavior (e.g. Qwen3 thinking mode), and responses cached
  under one setting must never replay under another.
- Reasoning models that spend the whole `max_tokens` budget thinking and
  return empty content now fail loudly instead of silently producing a
  zero-candidate cell: an empty response with `finish_reason=length` is a
  retryable error.

### Changed

- `docs/example-report.md` is now rendered from the tracked
  `results/exp_api27b_smoke/` artifact (one real-endpoint cell,
  thinking-off protocol), replacing the render of an untracked local run.

## [0.2.0] — 2026-09-29

The reproducibility release: the published numbers become one-flag
reproducible, and every cost figure either carries its price source or does
not appear.

### Added

- `run_experiment.py --preset published` pins the parameters of the three
  published 90-cell grids (16 mutants / target, 3 candidates / round, 2
  feedback rounds, gate reruns x3) that were previously only recorded in
  prose; `--preset published-b5` pins the B5 ablation grids (24 / 4 / 4).
  Precedence: explicit flag > preset > default. The runner now echoes the
  effective grid parameters at start so every log self-documents.
  Grid fingerprints to verify against are in `testforge/presets.py`
  (`max(mutants_total)`, `max(n_generated)`, `max(rounds_used)`).
- `REPRODUCE.md`: clone → install → one command → expected numbers.
- `pricing.json`: optional price table with mandatory provenance (source URL
  + effective date per entry). Ships empty on purpose.
- `TESTFORGE_PRICE_INPUT_PER_M` / `TESTFORGE_PRICE_OUTPUT_PER_M` env
  overrides; the source of every price travels with the results
  (`cost.price_source`) and into reports.

### Changed

- Cost accounting is honest by default: `config.py` no longer hard-codes
  placeholder unit prices. Without an explicit price, reports show exact
  token counts and "n/a" for USD instead of a fake-exact dollar figure.
  Legacy v0.1 archives (priced with undocumented placeholder rates) are
  reported as unpriced by `analyze.py`; the cache stores only text + tokens,
  so a price correction never invalidates the prompt cache.
- `analyze.py` gained a `--compare-with <exp_dir>` cross-model comparison
  section (per-variant MS, RQ1 uplift stats, gate ratio, token totals).

- CI: `mutation-loop-smoke` job runs one deterministic mock cell through the
  whole loop (analysis → mutation → generation → gate → joint evaluation) and
  asserts on the result, plus a pyflakes step; an additional manual
  `api-smoke` job exercises a real endpoint when repo secrets are configured
  (skips green otherwise).

### Fixed

- `pyflakes` — a documented repo gate — was missing from every dependency
  group; a rebuilt venv silently lost the gate. It is now in
  `pip install -e .[dev]`.
- `TESTFORGE_MODE` now works as the default for `--mode` in both the CLI and
  the experiment runner (previously the CLI flag always overrode it).
- The version number has a single source of truth
  (`testforge/__init__.py`, read by setuptools at build time).

## [0.1.0] — 2026-09-19

Initial public version: AST static analysis → 7 mutation operators →
kill-matrix execution (`pytest -x`, process pool) → LLM candidate generation
(deterministic Mock / any OpenAI-compatible endpoint, disk cache) →
multi-signal acceptance gate → surviving-mutant feedback loop → joint
evaluation → paired statistical analysis (hand-written Wilcoxon /
bootstrap, zero heavy dependencies). Six experiment variants B0–B5 over 18
deterministic pure functions; real-LLM grids on Qwen3-VL-8B and an offline
Mock grid, all archived under `results/exp_*`.
