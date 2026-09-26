# TestForge · 把变异分数当作验收标准的测试生成智能体

> 用途：给第一次打开这个仓库的人。看完知道它是什么、能不能解决你的问题、怎么不联网跑一遍。

LLM 生成的单元测试常常“能通过、但抓不住 bug”：它照着当前代码写断言，覆盖率涨了，行为变了却不报错。
TestForge 把验收标准换成变异测试——先给目标函数注入一批小改动（变异体，mutant），候选测试必须在
原代码上稳定通过、并且至少杀死一个既有测试杀不死的变异体才收进套件；没被杀死的变异体以 diff 形式
回填给模型再迭代一轮。每条被验收的测试都带着“它杀死了哪个变异体”的证据。

设计对应 Meta 在 FSE 2025 发表的 ACH（*Mutation-Guided LLM-based Test Generation at Meta*），
本仓库是它的开源端到端实现加配对实验。论文式报告在 [docs/report.md](docs/report.md)，本文件只作门面。

## 30 秒跑通（离线，不联网）

在仓库根目录执行（Linux/macOS 把 `.venv/Scripts/python.exe` 换成 `.venv/bin/python`）：

```bash
.venv/Scripts/python.exe -m testforge.cli targets
```

输出 18 行目标 id。再跑一条完整链路（分析 → 变异 → 生成 → 门禁 → 反馈 → 报告），本机实测 49 秒：

```bash
.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock
```

真实输出（`--mode mock` 是确定性离线后端，全程不发网络请求）：

```text
numeric.integer_sqrt                     B3  MS(all)= 76.2%  MS(cov)= 76.2%  gen=8   acc=2        49s
```

`MS(all)` 为最终套件的变异分数（被杀死的变异体占比），`MS(cov)` 只统计被执行到的变异体，
`gen`/`acc` 为生成数与被验收数。产物落在 `results/runs/`（JSON 明细 + `summary__B3.md`）。
把那格 JSON 再渲染成单目标 Markdown 报告：

```bash
.venv/Scripts/python.exe -m testforge.cli report --results results/runs/numeric.integer_sqrt__B3.json --out my_report.md
```

Mock 后端按种子运行：同一条命令跑两遍，两次 JSON 除 `wall_sec` 外逐字段相同（复核命令见
[AGENTS.md](AGENTS.md)）。完整流程、参数与故障对照见 [docs/getting-started.md](docs/getting-started.md)。

## 能力一览

| 想做什么 | 用什么 | 细节 |
|---|---|---|
| 给基准里的一个函数生成并验收测试 | `run --target numeric.integer_sqrt --variant B3 --mode mock` | [testforge/README.md](testforge/README.md) |
| 在你自己的 `.py` 上跑 | `run --module 路径 --function 函数名 --tests 已有测试` | [手册第 5 节](docs/getting-started.md) |
| 换实验条件做对照 | `--variant B0`（只跑既有套件）…`B5`（反馈不早退） | `testforge/variants.py` |
| 只看单个结果 JSON 的报告 | `report --results <json> --out <md>` | `testforge/report/renderer.py` |
| 跑完整网格、出统计与图 | `experiments/run_experiment.py` / `analyze.py` / `plots.py` | [experiments/README.md](experiments/README.md) |
| 接真实 LLM 端点 | `.env` 里配端点变量 + `--mode api` | [手册第 4 节](docs/getting-started.md) |

## 结果概览

仓库里提交了 8 个实验网格的产物（复核：`results/` 下 `exp_` 开头的目录数；`results/` 里其余目录是本机
历史残留，不在版本库内），下列数字都能从对应文件直接读到。

| 后端 | 结论 | 值 | 复核 |
|---|---|---|---|
| 真实 LLM（Qwen3-VL-8B，自建 vLLM） | 生成把平均变异分数抬高 | 77.6% → 91.3%（B0 → B1） | `results/exp_api_full/analysis.md` 的 Aggregate 表 |
| 真实 LLM | 两轮独立采样网格配对提升 | +12.7 个百分点（n=36，p=0.0001，95% CI [+8.5, +17.2]） | `results/exp_api_full/compare.md` |
| 真实 LLM | 门禁把验收测试数减半而分数不降 | 1.28 → 0.61 个/目标，MS 同为 91.3%（B1 → B2） | 同上 Aggregate 表 |
| 真实 LLM | 取消“零验收即早退”后的增量（B5 对 B2） | +4.2 个百分点（n=36，p=0.0115，CI [+1.8, +7.1]） | `results/exp_api_rq2full/compare.md` |
| 离线 Mock | 覆盖率与检出力解耦：无门禁多收测试，分数不变 | 行覆盖率 91.5% 对 87.2%，MS 同为 85.5% | `results/exp_mock_full/analysis.md` |
| 离线 Mock | 门禁按可证伪性拒掉的候选数 | 53 次（B3、B4 各 53） | 同文件末尾 Gate behaviour 表 |

验收测试长什么样、以及它杀掉了哪几个变异体，见 [docs/example-report.md](docs/example-report.md)
（真实模型生成的单目标报告，含逐变异体的杀伤归因表）。

## 目录怎么分

| 目录 | 负责 |
|---|---|
| `testforge/` | 包本体：静态分析、变异引擎、门禁、Agent 回路、LLM 后端、报告、CLI |
| `benchmarks/` | 6 模块 × 18 个目标函数，每个模块配一份刻意不完整的既有测试（B0） |
| `experiments/` | 网格运行、配对统计、出图、跨网格比较 |
| `tests/` | 自身的 49 个测试（复核：`.venv/Scripts/python.exe -m pytest --collect-only`，末行 `49 tests collected`） |
| `results/` | 实验产物（JSON、Markdown、PNG），只读不改 |
| `docs/` | 技术报告、示例报告、面试手册、上手手册 |

各目录的逐文件说明见对应的 `README.md`；被多处引用的事实统一记在 [AGENTS.md](AGENTS.md)。

## 已知做不到什么

1. Mock 后端不等于真实模型。它是“先跑一遍函数、把观测值冻成断言”的特征化生成器，杀得掉常量与
   算子类变异体，造不出需要理解语义的预言机（例如 `parse_csv_line` 的引号转义边界）。它用于验证
   门禁与回路的机制，不能用来主张生成质量。
2. 效果结论只到 8B 规模。两轮真实网格用的是自建 vLLM 上的 Qwen3-VL-8B，更大模型未测。
3. `--mode api` 必须有一个可用的 OpenAI 兼容端点。`.env` 里 `DEEPSEEK_API_KEY` 为空时命令立刻以
   退出码 1 结束并给出提示，不会带着空凭据发请求。
4. 基准是 18 个确定性纯函数、单一语言（Python）。等价变异体无法穷尽排除，变异分数因此是下界。
5. 报告里的美元成本不可信：`testforge/config.py` 的单价是占位值。逐笔 token 数是精确的。

## 环境要求

Python 3.10 以上（本仓库自带 `.venv`，实测 3.12.0），依赖 `pytest` / `coverage` / `openai` /
`matplotlib`（清单见 `pyproject.toml`）。离线 Mock 全流程不需要网络，也不需要把本包装进解释器——
所有命令都在仓库根以 `python -m ...` 运行，`testforge` 未装进 `.venv`（复核：`pip list` 查不到它）。

## 许可

MIT，见 [LICENSE](LICENSE)。

---

准备改这个仓库的 AI 助手请先读 [AGENTS.md](AGENTS.md)。
