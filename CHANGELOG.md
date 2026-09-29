# Changelog

All notable changes to TestForge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/): breaking the documented CLI/config contract
bumps the major, added capability the minor, fixes the patch.

## [Unreleased]

### Added

- `TESTFORGE_TRANSPORT=urllib`: a stdlib HTTP transport for the
  OpenAI-compatible backend, alongside the default SDK transport. Some campus
  gateways WAF-block the SDK's HTTP stack with an HTML "access denied"
  interstitial while serving plain requests fine (verified against
  openapi.seu.edu.cn: curl and urllib pass, the SDK transport is rejected);
  the urllib transport uses the identical wire format and gets through.
- `TESTFORGE_MIN_CALL_INTERVAL_SEC`: minimum gap between real (non-cached)
  API calls, process-wide, for gateways that throttle request bursts.
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
