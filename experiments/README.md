# experiments/ —— 网格、统计与图

> 用途：说明这四个脚本各自跑什么、参数怎么写、产物落在哪里、哪些命令会覆写仓库里的文件。
> 全部脚本从仓库根执行：`.venv/Scripts/python.exe experiments/<脚本>.py ...`。

一条实验链是三步：`run_experiment.py` 跑出网格 → `analyze.py` 出配对统计 → `plots.py` 出图；
`compare_grids.py` 把两张同设计的网格并到一起做重复性检验。统计部分只用标准库，出图只用 matplotlib。

## 文件清单

| 文件 | 干什么 | 关键行为 |
|---|---|---|
| `run_experiment.py` | 跑（目标 × 变体）网格，崩溃可续 | 每格跑完立刻重写整份 `results.json`；重启时已完成格打印 `skip ... (cached)`；带 `error` 键的格先归档到同目录 `errors.json` 再重跑；结束时写 `summary.md` |
| `analyze.py` | 配对统计 → `analysis.md` + `analysis.json` | 手写 Wilcoxon 符号秩（正态近似 + 并列校正）与 bootstrap 95% CI（10,000 次重采样，种子 7）；跳过带 `error` 的格 |
| `plots.py` | 6 张 PNG 到 `<exp>/plots/` | 条件不满足时直接不画那张图（见下） |
| `compare_grids.py` | 两网格重复性检验 → 写到 A 目录的 `compare.md` | `--treat` / `--base` 默认 B1/B0；已发表的 `results/exp_api_rq2full/compare.md` 用的是 `--treat B5 --base B2` |

## 参数

`run_experiment.py`：

| 参数 | 作用 | 默认 |
|---|---|---|
| `--mode` | `mock`（离线）或 `api`（真实端点） | `mock` |
| `--targets` | `all` 或逗号分隔目标 id | `all` |
| `--variants` | 逗号分隔变体名，未定义的直接报错 | `B0,B1,B2,B3,B4` |
| `--max-mutants` | 每目标变异体上限（超过按算子分层采样） | 24 |
| `--candidates` | 每轮向模型要几个候选 | 4 |
| `--rounds` | B3/B4/B5 的最大反馈轮数（B0–B2 用自己的定义） | 3 |
| `--flaky-runs` | 门禁在原代码上重复几次 | 5 |
| `--out` | 输出目录，相对仓库根解析 | `results/exp_<mode>_<时间戳>` |

`analyze.py` 与 `plots.py` 都只接 `--exp <目录>`（`plots.py` 另有 `--label`）；
`compare_grids.py` 接 `--a`、`--b`、`--treat`、`--base`。

## 冒烟：一次完整的离线实验链

```bash
.venv/Scripts/python.exe experiments/run_experiment.py --mode mock --targets numeric.clamp,numeric.moving_average --variants B0,B1 --out ../tf_smoke
.venv/Scripts/python.exe experiments/analyze.py --exp ../tf_smoke
.venv/Scripts/python.exe experiments/plots.py --exp ../tf_smoke --label "smoke"
```

本机实测 4 格约 25 秒（4/4/6/11 秒），输出末行 `done -> <仓库根>\..\tf_smoke`，
随后两条分别输出 `analysis -> ..\tf_smoke\analysis.md` 与 `plots -> ..\tf_smoke\plots`。
同一个 `--out` 再跑一次会逐格打印 `skip ... (cached)`。跑完删掉临时目录。

## 产物长什么样

| 文件 | 谁写的 | 内容 |
|---|---|---|
| `results.json` | `run_experiment.py` | 一格一条记录，字段等于 `VariantResult` 的全部字段（含 `mutant_summary`、`gate_log`、`accepted_codes`）外加 `cost` |
| `summary.md` | `run_experiment.py` | 一行一格的 MS / 覆盖率 / 生成数 / 验收数 / 成本表 |
| `errors.json` | `run_experiment.py` | 只在续跑时把出错格归档到这里才出现 |
| `analysis.md` / `analysis.json` | `analyze.py` | 聚合表、LLM 用量、逐目标分数与提升、RQ 配对检验、门禁行为 |
| `plots/*.png` | `plots.py` | `ms_by_variant`、`ms_heatmap`、`uplift_per_target`、`tokens_by_variant`、`uplift_vs_cost`、`gate_rejections` |
| `compare.md` | `compare_grids.py` | 两网格各自的配对均值、pooled 的 Wilcoxon 与 bootstrap CI、两条一致性检查 |

`analyze.py` 里的研究问题是硬编码的：RQ1 B1−B0、RQ2 B3−B1、RQ3 B2−B1、RQ4 B4−B3、RQ5 B5−B2。
缺哪个变体就跳过哪条，所以只跑 `B0,B1` 的网格只出 RQ1。

## 图为什么有时少几张

三张图带跳过条件，代码里是提前 `return`：`tokens_by_variant.png` 在全部 token 为 0 时不画
（Mock 网格就是这样），`uplift_vs_cost.png` 需要同时有 B0 和 B3，`gate_rejections.png` 在六种拒绝
计数全为 0 时不画。缺图不是失败，`plots.py` 的退出码仍是 0。

## 和谁打交道

- **上游**：`benchmarks/manifest.json`（经 `testforge.benchmarks.load_targets()`）、
  `testforge/variants.py`（变体表）、`testforge/report/renderer.py`（`summary.md` 由它渲染）。
- **下游**：`results/` 下的产物被 README、`docs/report.md` 引用。
- **改这里之后要跑**：冒烟链三条命令 + `.venv/Scripts/python.exe -m pytest`。

## 别动

- 不要把 `analyze.py` 或 `plots.py` 指向 `results/` 下的已发表网格：它们会就地覆写
  `analysis.md`、`analysis.json`、`plots/*.png`、`compare.md`。要重算就先把网格目录拷到临时位置。
- 不要用当前默认参数去“复现”已发表的三张 90 格网格：那三张用的是
  `--max-mutants 16 --candidates 3 --rounds 2`，与默认的 24 / 4 / 3 不同（复核：读对应
  `results.json` 里 `mutants_total` 与 `n_generated` 的最大值）。
- 不要给 `analysis.json`、`compare.md` 加构建时间戳或本机绝对路径：它们进版本库，
  加了就会每次重跑都产生幻影 diff。
- `run_experiment.py` 末尾用 `VariantResult(**{...})` 从 JSON 反推出对象再渲染 `summary.md`，
  所以给 `VariantResult` 加字段时要确认老 `results.json` 里没有该字段也能跑（它有 `field(default_factory)` 兜底）。
