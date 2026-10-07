# results/ —— 实验产物存档（只读）

> 用途：给要引用或核对已发表数字的人。交代各命名前缀对应哪个历史批次、哪些目录是白名单
> 入库的已发表网格、旧 analysis.md 与重算版的时间差。所有数据文件只读：不重命名、不改内容。

## 文件清单

15 个入库目录、75 个文件。`.gitignore` 白名单只放行 `results/exp_*/` 下的 results.json /
analysis.md / analysis.json / summary.md / compare.md / analysis_v2.md / analysis_v2.json /
plots/*.png，外加本说明；目录里其余文件（errors.json、日志等）不入库。命名前缀对应的历史批次：

| 目录 | 时期与发布 | 内容 |
|---|---|---|
| `exp_api27b_full`、`exp_api27b_replicate` | v0.4.0（2026-09-30）起，qwen3.8-27B 单模型口径 | 已发表主网格（90 格）的两次独立采样，pooled RQ1 在 `exp_api27b_full/compare.md` |
| `exp_api27b_rq2full`、`exp_api27b_rq2full_rep` | 同上 | 已发表 B5 全预算网格（24 变异体口径）的两次采样，pooled 在 `exp_api27b_rq2full/compare.md` |
| `exp_api27b_smoke` | 同上 | 24 变异体全强度单格冒烟，`docs/example-report.md` 的渲染来源 |
| `exp_v05_*`（9 个：base / both / cap6_base / cap6_priority / incremental / priority / property / time_base / time_inc） | v0.5.0 | Mock 基准开关矩阵研究（incremental / priority / property 三开关及其组合、6 变异体上限、计时对照） |
| `exp_mock_full` | Mock 协议的已发表 90 格网格 | docs/REPRODUCE.md 第 2–4 步的对照基准；`analysis.md` 是旧脚本产物（见下），重算版在同目录 `analysis_v2.md` |
| `exp_mock_published_repro` | 复现证据 | docs/REPRODUCE.md 第 2 步 `--preset published` 的重跑产物，第 3 步与 `exp_mock_full` 比对指纹 |
| `exp_api_*`（8B 时期） | v0.1–v0.3，Qwen3-VL-8B | 已随 v0.4.0 从工作区移除，档在 tag v0.3.0；本机残留 `exp_api_rq2full/`（仅 errors.json）不入库、不引用 |

**已发表协议网格**（docs/report.md 与 docs/REPRODUCE.md 的数字出处）是白名单入库的这五个：
`exp_api27b_full`、`exp_api27b_replicate`、`exp_api27b_rq2full`、`exp_api27b_rq2full_rep`
（真实 LLM）与 `exp_mock_full`（Mock 协议）。其余入库目录是配套证据：smoke 冒烟、repro
复现、v0.5 开关矩阵。

**旧 analysis.md 的时间差说明**：`exp_mock_full/analysis.md` 由旧版 analyze.py 生成，比现行
脚本少「LLM usage per variant」与「Per-target uplift (B1 minus B0), sorted」两节；同目录
`analysis_v2.md` / `analysis_v2.json` 是用现行脚本重算的完整版，并把 v0.1 占位单价算出的美元列
按"未定价"处理。两个版本都保留：docs/REPRODUCE.md 引用的是 analysis.md 里的已发表原样数字。

## 和谁打交道

- **上游**：`experiments/run_experiment.py`（results.json、summary.md）、`analyze.py`
  （analysis.md / analysis.json）、`compare_grids.py`（compare.md）、`plots.py`（plots/*.png）。
- **下游**：docs/report.md、docs/REPRODUCE.md、README.md、AGENTS.md 引用这里的数字与图。
- **改这里之后要跑**：无。本目录是存档，改生成脚本只影响以后新跑的目录，不回写这里。

## 别动

- 已提交的产物不改、不删、不重命名（命名不一致是历史批次，不"纠正"）；要新数字就跑进新目录
  再改文档引用（docs/GIT.md 的铁律）。
- `exp_mock_full/analysis.md` 不要用现行脚本重算覆盖——docs/REPRODUCE.md 引用的是它的原样数字，
  完整版已经在旁边的 `analysis_v2.md`。
- `exp_v05_*` 部分格子改过开关（incremental / priority / property / 6 变异体上限），绝对分数
  不与主网格直接比较，只在同网格内做配对。
- `exp_api_rq2full/`（仅 errors.json）是白名单外的本机残留，禁止入库，也不要当数据引用。
