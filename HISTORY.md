# HISTORY —— 版本更新记录

> 用途：记录 TestForge 每个版本的全部显著变更。只追加，禁止删除或改写既有条目；写错了就追加
> 一条更正。新条目写在文件末尾。
> 版本语义沿用 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 与
> [SemVer](https://semver.org/)：破坏已文档化的 CLI/config 契约升 major，新增能力升 minor，
> 修复升 patch。0.1.0–0.6.0 各条目由原 `CHANGELOG.md` 逐条无损转入（2026-10-05），内容未改写。

## 2026-09-19 · v0.1.0 Initial public version

Initial public version: AST static analysis → 7 mutation operators →
kill-matrix execution (`pytest -x`, process pool) → LLM candidate generation
(deterministic Mock / any OpenAI-compatible endpoint, disk cache) →
multi-signal acceptance gate → surviving-mutant feedback loop → joint
evaluation → paired statistical analysis (hand-written Wilcoxon /
bootstrap, zero heavy dependencies). Six experiment variants B0–B5 over 18
deterministic pure functions; real-LLM grids on Qwen3-VL-8B and an offline
Mock grid, all archived under `results/exp_*`.

## 2026-09-29 · v0.2.0 The reproducibility release

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

## 2026-09-30 · v0.3.0 The external-validity release

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

## 2026-09-30 · v0.4.0 The single-model release

The single-model release: every real-LLM result in the project now comes from
one model, qwen3.8-27B, with the 8B era archived at tag v0.3.0.

### Added

- Second independent samplings on qwen3.8-27B for both published protocols,
  completing the two-sampling structure the statistics require:
  `results/exp_api27b_replicate` (90 cells) and `results/exp_api27b_rq2full_rep`
  (54 cells) — both zero errors, run with 10 s call pacing after the gateway's
  HTTP 420 throttling window.
- Pooled statistics for the unified single-model story
  (`docs/report.md` rewritten end to end):
  RQ1 (B1−B0, n=36 pooled): **+14.9pp, 25 wins / 0 losses, p<0.0001,
  CI [+10.4, +19.8]**; gate: accepted tests cut to 40-44% at equal mutation
  score; RQ5 (B5−B2, n=36 pooled): **+2.9pp, 5 wins / 0 losses, p=0.0422,
  CI [+0.7, +5.8]** — with `parse_csv_line`'s quote-escape survivor, the hard
  core of the 8B era, closed by the feedback loop at round 4.

### Changed

- **Model history unified (§6.8)**: report.md now presents all results as
  qwen3.8-27B; the v0.1–v0.3 Qwen3-VL-8B grids (`results/exp_api_*`) were
  removed from the working tree and remain retrievable at tag v0.3.0. B0 —
  which contains no model randomness — is bit-identical across both eras
  (77.6% / 77.2%), anchoring protocol invariance.
- Case studies re-anchored to 27B data: the feedback-loop win is now
  `numeric.integer_sqrt` (81.2% → 87.5%, round 2, sampling 2); the
  `parse_csv_line` difficulty marker closes at round 4 under the B5 budget.

## 2026-09-30 · v0.5.0 The efficiency-and-generation-space release

The efficiency-and-generation-space release: three independent, optional-by-default upgrades from the roadmap (docs/report.md §8), each leaving the published grids' default behavior bit-for-bit unchanged.

### Added

- **Mutant priority sampling** (`--mutant-priority` / `TESTFORGE_MUTANT_PRIORITY`):
  the mutant budget fills with baseline-covered-line mutants first (PRIMG-style),
  falling back to uncovered lines only if the budget allows. Priority sampling
  changes WHICH mutants are sampled — off by default so published grid
  fingerprints stay valid.
- **Incremental mutant execution** (`--incremental` / `TESTFORGE_INCREMENTAL`):
  mutants whose mutated line the suite under test never executes are recorded
  PASS without spawning a subprocess — unreachable code cannot change observed
  behavior, so outcomes are provably identical while the kill-matrix cost
  drops to the covered fraction. The toggle changes cost, never outcomes.
- **Property-based mock generation** (`--property` / `TESTFORGE_PROPERTY`,
  optional `hypothesis` dependency in `.[property]`): the Mock backend gains a
  hybrid generation mode — each candidate keeps the characterization
  exact-value probes and gains a deterministic behavioral-envelope property
  (`@given`, `derandomize=True`, `database=None`) asserting that over a frozen
  input domain the function only returns observed types / raises observed
  exception classes and is deterministic. Kills are a strict superset of
  characterization mode; the feedback signal and the gate are unchanged.
- Toggle-matrix study on the mock benchmark (`results/exp_v05_*`, 9 grids):
  incremental execution is outcome-identical on all 18 targets x 8 fields
  (wall 912s -> 884s serial; savings scale with the uncovered share, ~3% on
  this ~83%-coverage benchmark); priority sampling only binds under budget
  pressure (identical at the 24-mutant default, where ~11 candidates/target
  never cap; at a 6-mutant cap MS(all) rises 88.7% -> 90.6%, 2 wins / 0
  losses); the property hybrid kills a strict superset of characterization
  kills and adds one grid win (integer_sqrt 76.2% -> 81.0%) at ~+30% test
  execution time.

## 2026-09-30 · v0.6.0 The landing release

The landing release: the project becomes its own GitHub Action, gains a PR
quality gate and a whole-package batch mode, and installs a `testforge`
command.

### Added

- **Repository = Action** (root `action.yml`, composite): inputs for
  mode/endpoint/variant/caps; computes the PR diff, runs the gate, attaches
  the summary to `$GITHUB_STEP_SUMMARY` and optionally posts/updates a PR
  comment (marker-deduplicated). Advisory by default — suggested tests are
  proposed in the comment, a human merges.
- **`testforge ci`** (testforge/pr_gate.py): diff → changed-function discovery
  (testforge/diff_targets.py, stdlib unified-diff parsing + AST spans) →
  budgeted per-target runs → summary.md. Exit code is non-zero only for
  infrastructure errors (a target could not be run); a low mutation score is
  information, not a failure.
- **`testforge batch`** (testforge/batch.py): whole-package scan for public
  top-level functions, priority queue (no existing tests first, then fewer
  existing tests, then name order), one shared Budget, crash-safe per-target
  results.json + batch-summary.md with suggested tests.
- **Budget as a first-class control** (testforge/budget.py): wall-clock and
  token ceilings shared by everything that receives them; an exhausted budget
  stops the generation loop cleanly while the final joint evaluation still
  runs, so every started target keeps a mutation score
  (`VariantResult.budget_exceeded`).
- **Console entry point**: `pip install testforge` now provides `testforge ...`
  (`[project.scripts]`).
- Dogfood workflow (`.github/workflows/quality-gate.yml`): testforge's own PRs
  are gated by the action in mock mode (deterministic, zero cost).
- 8 new tests (diff parsing, ci end-to-end, budget early-stop, batch
  discovery/ordering/execution) — 91 total.

## 2026-10-05 · 文档规范体系落位

- 文档从"五件套"迁到九件体系：新增 `docs/ARCHITECTURE.md`、`docs/CODE-STYLE.md`、
  `docs/TESTING.md`、`docs/GIT.md`、`HISTORY.md`、`TODO.md`；`docs/getting-started.md`
  更名 `docs/GET-START.md`；`AGENTS.md` 重写为规范入口（原「仓库地图」与 9 条关键约定
  移入 ARCHITECTURE，原「改动后的验证」移入 TESTING，「当前真实状态」更名「当前状态」
  保留全部数字与复核命令）。
- `CHANGELOG.md` 并入本文件（上方 v0.1.0–v0.6.0 条目逐条保留、原文未改写），原文件删除。
- 变更缘由：落位《项目整体规范.md》九件必建。

## 2026-10-06 · 文档核查修复（0.6 交付物回写 + 旧值清零）

- **包说明对齐 0.6.0**：testforge/README 顶层 `.py` 7→12（补 batch/budget/diff_targets/
  pr_gate/presets 五行，标注 0.6 新增）、版本 0.1.0→0.6.0、cli 子命令 3→5（ci/batch）。
- **旧值清零**：AGENTS editable 条目 0.2.0→0.5.0（并注明元数据落后源码一版）、
  「现为 83」→91；tests/README 引用 AGENTS「83 个测试」→91；GET-START 两处
  `49 passed`→91；ARCHITECTURE 与 AGENTS 的 example-report 来源 api_smoke→
  `results/exp_api27b_smoke/`（api_smoke 已删）。
- **杂项**：benchmarks/README 登记 numeric.py 的第 4 个函数 `demo_gate_probe`
  （未进 manifest、零引用，留待决断）；experiments/README 用途行去掉 `<脚本>` 占位；
  GET-START 示例 `--target <新 id>` 改真实 id `numeric.clamp`；TODO「正在做」更新；
  目录说明补 `action.yml`（此前漏登的 GitHub Action 入口）。

## 2026-10-07 · 复杂度收尾（statistics 换手写统计 + 删 presets 死函数）

- `experiments/analyze.py` 手写的 `_mean/_median/_stdev` 换 `statistics` 标准库
  （fmean/median/stdev，空列表护栏行为保留）。等价性实测：16 个已发表网格 + 2 组
  compare 对用改前/改后代码各重算一遍，analysis.md / analysis.json / compare.md
  全部字节一致。
- 删 `testforge/presets.py` 的 `apply_preset`：全仓零生产调用——网格侧由
  `run_experiment.resolve_params` 自行实现「旗标 > 预设 > 默认」，CLI 无 `--preset`
  入口；连带删其 2 项专项测试（91→89）。preset→参数映射仍有
  `test_resolve_params_published_preset_matches_archive` 钉住。
- 文档同步：AGENTS / README / ARCHITECTURE / GET-START / tests/README 的测试数
  91→89；tests/README 的 test_presets 条目改 6 项。

## 2026-10-07 · results/ 存档说明补齐（results/README.md）

- 新增 `results/README.md`（`.gitignore` 白名单加一行入库）：交代命名前缀与历史批次的
  对应（`exp_api27b_*` = v0.4.0 起 qwen3.8-27B、`exp_v05_*` = v0.5.0 Mock 开关矩阵、
  `exp_api_*` = v0.1–v0.3 的 8B 时期已档在 tag v0.3.0）、白名单入库的五个已发表协议
  网格（27B 主网格与 B5 网格各两次采样 + `exp_mock_full`）、`exp_mock_full/analysis.md`
  缺「LLM usage per variant」与「Per-target uplift」两节的时间差（重算版
  `analysis_v2.md` 在同目录）；并登记 `exp_api_rq2full/` 为不入库的本机残留。
- 数据文件零改动、零重命名；目录说明、docs/GIT.md、AGENTS、ARCHITECTURE、.docsignore
  的入库边界描述同步。

## 2026-10-12 · REPRODUCE.md 四步复现核验（任务 2 挂账清零）+ 复现文档修正

- **四步端到端跑通（离线，零网络）**：fresh `--out`（`../tf_repro_mock_published`，仓库外）
  90/90 格 ok、0 错误、总耗时 3104 秒（Windows 11、Python 3.12.0、20 核、机器重载）。
  指纹 (16, 6, 2, 90) 在 fresh 网格、归档 `exp_mock_full`、已入库的
  `exp_mock_published_repro` 三处一致。
- **位级复现范围查明**：B0 全部 18 格位级一致；90 格中 84 格位级一致。漂移的 6 格
  （numeric.integer_sqrt B1/B2、numeric.moving_average B1–B4）根因 = v0.1 归档之后
  fd98f6f 给 `benchmarks/targets/numeric.py` 末尾追加 `demo_gate_probe`（2026-10-06 已
  登记「留待决断」），mock 种子含 `len(module_source)` → 该模块 mock 候选全部换样。
  当前代码确定性已复核：同格重跑 JSON 除 wall_sec 逐字节一致。已发表统计结论在 fresh
  网格复现：RQ1 +6.5pp（归档 +7.8pp）、8/10/0（9/9/0）、Wilcoxon p=0.0115（0.0076）、
  CI [+3.0,+10.2]（[+4.0,+11.8]）。
- **单格默认参数复测**：MS 76.2%、acc 2 不变，gen 8→12（同一机制）；AGENTS「当前状态」
  与 GET-START §3 的期望输出同步更新。
- **REPRODUCE.md 修正**：除本批前已提交的三处断链（Step 4 目录对齐、plots 可选组说明、
  数字出处改引 analysis_v2.md）外，「Mock 网格位级一致」表行补范围（同代码 + 未改动的
  目标模块文件）、Step 4 增 2026-10-12 核验记录（含 `git checkout bfe4161 --
  benchmarks/targets` 可逐格位级复现归档）、单格注释 gen 8→12；AGENTS「已知坑」新增
  mock 种子条目。
- **TODO 收口**：任务 2 完成；任务 6（`demo_gate_probe` 去留裁决）挂账；
  ponytail-audit 清理另挂任务 4/5（18565e2）。
- 数据文件零改动：`results/` 已提交产物、`llm_cache/` 均未触碰。

## 2026-10-12 · audit 小清理（任务 4，九项零行为变化）

- 按 2026-10-12 ponytail-audit 挂账执行，净 -14 行，零行为变化：删 `Candidate` 死字段
  `llm_calls/tokens_in/tokens_out/cost_usd`（全仓无人写、不序列化）；`_payload_from` 双份
  （batch.py/pr_gate.py）合并为 `benchmarks.result_payload`（cli 与 run_experiment 的同款
  两行一并复用，共四处）；`_mutant_job` 去掉调用方都丢弃的 duration（连带删 runner.py 的
  `import time`）；`_maybe_repair` 去掉调用方未用的 `did_repair`；内联单行包装 `_fmt`；
  删模块级 `split_candidates` 包装（test_mock_client 改用 `LLMResponse(...).split_candidates()`）；
  analyze.py 的 `agg["ms_all"]` 去掉包 list 再解包（analysis.json 输出字节不变）；
  `new_work_root` 内联进 `workspace`；cli.py 的 `__import__(...)` lambda 改函数内常规导入
  （`_cmd_ci`/`_cmd_batch`）。
- 门禁：pytest 89 过、pyflakes 0、离线单格 MS 76.2%/gen 12/acc 2 不漂移。

## 2026-10-12 · `_find_existing_tests` 双份合并为 `utils.find_existing_tests`（任务 5）

- **方案说明**：两份拷贝的搜索顺序相同（模块旁 → `<root>/tests` → 包层 rglob），差别只在
  第三段——batch 从 `module_path.parent` 起 rglob，pr_gate 从 `parent.parent` 起 rglob
  （batch 另有对 candidates[0] 的去重，纯装饰：首中即胜使重复候选无害）。合并口径：
  第三段取「模块上两层目录，但绝不越过 root」——`parent.parent` 在 root 内（等于 root
  或是其子孙）则搜它（rglob 向下覆盖模块自身目录，是 batch 原第三段的严格超集），
  否则退回 `parent`（batch 顶层模块行为逐字节保留）。
- **行为变化（仅两处，均为超集或有界化）**：batch 的嵌套模块（pkg/sub/mod.py）搜索范围
  从 pkg/sub 扩到整个 pkg——只增不减；pr_gate 的仓库根级文件原本会 rglob 到仓库之外
  （root 的父目录），现收敛为 root 之内。其余情形候选集合与优先级不变。
- **测试**：合并前两份拷贝均无直接单测；兄弟文件命中路径由
  `test_batch_discovery_orders_by_existing_coverage_then_name` 与
  `test_ci_runs_changed_targets_and_writes_summary` 间接覆盖，覆盖水平与合并前一致。
- 门禁：pytest 89 过、pyflakes 0。

## 2026-10-12 · 移除 `demo_gate_probe`，恢复已发表网格逐格位级复现（任务 6）

- **裁决：移除**。理由：函数自述 Safe to remove、全仓零代码引用、2026-10-06 起登记
  「留待决断」，且它经 mock 种子（含 `len(module_source)`）破坏已发表网格的位级可复现——
  可复现性是 v0.2 起的核心承诺；保留则 REPRODUCE/GET-START/AGENTS 三处永久背负漂移脚注。
  `benchmarks/targets/numeric.py` 以 `git checkout bfe4161 --` 恢复 v0.1 字节（对归档
  diff 为空）。
- **复验**：六个漂移格（integer_sqrt B1/B2、moving_average B1–B4）重跑，现 schema 共同键
  逐字段与归档全等，ms_all 回到 0.750 / 1.000；单格默认参数回到 MS 76.2% / gen 8 / acc 2。
  两处不可比差异均为 schema 演进而非行为漂移：归档行多三个 v0.1 遗留字段
  （`b0_killed_final`/`n_repaired`/`flaky_rejects`，现输出已无）；归档 B0 格 `cost_usd`
  为 0.0（v0.2 起语义为未调用即 `null`）。
- **文档同步**：benchmarks/README 撤销 demo 探针登记；GET-START / AGENTS 单格期望回到
  gen 8；REPRODUCE.md 核验记录补 follow-up；AGENTS 已知坑保留机制警示并登记与归档的
  对照口径（按共同键比）。
- 门禁：pytest 89 过、pyflakes 0。

## 2026-11-02 · TF-01 并行污染假满分：suspect 不变量 + 渲染告警 + 串行前提登记

- **问题**（.workbuddy 2026-10-21 审查发现，2026-11-01 体检列 P1）：同机并行跑 pytest 与
  mock 单格会互相污染，单格可退化为 gen=0/acc=0/coverage 0% 却 killed_final=21/21、
  ms_all=1.0 的假满分。机制：`Outcome.killed_mutant` 把 ERROR/TIMEOUT 一律记杀（PIT 惯例），
  并发争用使变异体子进程 ERROR。串行不触发。
- **设计取舍**：三案比较——(a) ERROR/TIMEOUT 分桶计数要动杀伤矩阵与 payload 契约，改动大；
  (b) 被记杀变体补执行时长记录需逐格计时，同样大；(c) 结果级不变量最省：被杀变异体必经
  执行其所在行，killed>0 而 coverage=0 在串行下是矛盾签名，误报仅剩「coverage 子进程失败
  而杀伤矩阵正常」这一本身也该人工复核的异常。选 (c)，不改变任何结果值，只加标记。
- **实现**：`VariantResult.is_suspect` 属性；`result_to_dict` 落 `suspect` 字段（可审计）；
  `renderer.render_target_report` 顶部告警、`render_summary` 行内 `(SUSPECT)` 标记。
  `cli report` 从 JSON 重建时未知键被过滤，归档结果不受影响。
- **测试**：新增 `tests/test_suspect_invariant.py` 3 项：污染签名必标且两处渲染均告警、
  payload 带 suspect；强 B0 全杀但 coverage>0 的合法满分不误报；空结果与普通部分杀伤不误报。
  既有 89 项结果不变。
- **登记**：AGENTS 已知坑补「同机并行互相污染，门禁与单格/网格请串行」条目；`.workbuddy/`
  入 .gitignore（同 zhishuxing 处置；其发现已转录至本文件与 AGENTS）。
- **文档同步**：测试数 89→92（AGENTS「当前状态」、README 正文与徽章、TESTING、REPRODUCE、
  tests/README）；徽章 91→92 一并归正（即体检 TF-02）。
- 门禁：pytest 92 过、pyflakes 0、check_docs testforge 通过。

## 2026-11-11 · TF4-1 analyze.py 聚合表一行崩溃修复：`[0]` 下标去除 + analyze 首个冒烟测试

- **问题**（2026-11-11 体检列 P1，REPRODUCE 第 4 步 100% 复现）：任何非空网格跑
  `experiments/analyze.py` 必炸——`analyze.py:252` 聚合表渲染 `fmt_pct(agg[v]['ms_all'][0])`
  对 float 下标，`TypeError: 'float' object is not subscriptable`，REPRODUCE 第 4 步、
  GET-START §6、experiments/README 冒烟链、TESTING experiments 行全部不可用。
- **根因**：290592f（2026-10-12「audit 小清理九项(任务 4)……净 -14 行零行为变化」）把
  `agg["ms_all"]` 从 `[_mean(...)]` 改为标量并同步了 analysis.json 消费侧，但漏改 markdown
  聚合表的 `[0]` 消费者——「零行为变化」声明与事实不符，属该提交引入的回归。tests/ 对
  experiments/analyze.py 零覆盖，三条门禁全绿也拦不住（崩溃未被发现的原因）。
- **修复**：`analyze.py:252` 去掉 `[0]`（一行）。REPRODUCE 第 4 步复跑通过（退出码 0），
  重生成的 `results/exp_mock_published_repro/analysis.md` 与提交的回归前版本逐字节一致
  （git status 对该文件零 diff），数字与 REPRODUCE.md 期望表全符：B0 77.6%/80.6%、
  B1 85.5%/90.3%/2.50、B2/B3/B4 85.5%/90.3%/0.56；RQ1 +7.8% 9/9/0 p=0.0076 CI [+4.0, +11.8]。
- **测试**：新增 `tests/test_analyze.py` 2 项（analyze 的首批测试）：最小 2×2 网格冒烟
  （聚合表按标量均值渲染、analysis.json aggregate 为标量、RQ1 块存在）与全错误网格冒烟
  （错误表渲染不炸）。已验证对未修复代码必红（复现 TypeError 于 analyze.py:252）。
- **文档同步**：测试数 92→94、文件数 14→15（AGENTS「当前状态」与「已知坑」、README 正文
  与徽章、TESTING、REPRODUCE、tests/README 含文件清单与「改这里之后要跑」补 analyze 行）。
- 门禁：pytest 94 过（196.48s）、pyflakes 0。check_docs 由主流程统一跑（本批执行员不跑）。
