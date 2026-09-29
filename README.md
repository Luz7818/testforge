<div align="center">

# TestForge

**Mutation-guided test quality agent — LLM generates tests, mutation testing proves they catch bugs.**

[![CI](https://github.com/Luz7818/testforge/actions/workflows/ci.yml/badge.svg)](https://github.com/Luz7818/testforge/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://github.com/Luz7818/testforge)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-70%20passed-brightgreen)](#本地验证)
[![Reproducible](https://img.shields.io/badge/mock%20grid-bit--identical-informational)](REPRODUCE.md)

</div>

> 用途：给第一次打开这个仓库的人。看完知道它是什么、能不能解决你的问题、怎么不联网跑一遍；
> 细节与操作步骤在手册与报告里，本文只作门面。

LLM 生成的单元测试常常"能通过、但抓不住 bug"：它照着当前代码写断言，覆盖率涨了，行为变了却不报错。
TestForge 把验收标准换成变异测试——先给目标函数注入一批小改动（变异体），候选测试必须在原代码上
稳定通过、并至少杀死一个既有测试杀不死的变异体才收进套件；没被杀死的变异体以最小 diff 回填给模型
迭代强化。每条被验收的测试都带着"它杀死了哪个变异体"的证据。

设计对应 Meta 发表于 FSE 2025 的 ACH（*Mutation-Guided LLM-based Test Generation at Meta*），
本仓库是它的开源端到端实现加配对实验。

## 快速开始（离线，不联网）

```bash
git clone https://github.com/Luz7818/testforge.git
cd testforge
pip install -e .[dev]

python -m testforge.cli targets                                          # 列出 18 个基准目标
python -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock
```

真实输出（`--mode mock` 是确定性离线后端，全程不发网络请求；本机实测约 49 秒）：

```text
numeric.integer_sqrt                     B3  MS(all)= 76.2%  MS(cov)= 76.2%  gen=8   acc=2        49s
```

`MS(all)` 为最终套件的变异分数，`MS(cov)` 只统计被执行到的变异体，`gen`/`acc` 为生成数与被验收数；
产物在 `results/runs/`，用 `testforge.cli report` 渲染成带逐变异体杀伤归因的报告
（样例见 [docs/example-report.md](docs/example-report.md)，来源 JSON 已入库）。

## 功能特性

- **双后端**：确定性离线 Mock（重跑逐位一致）＋ 任意 OpenAI 兼容端点，prompt 磁盘缓存、重放零成本。
- **变异引擎**：7 类算子，仅变异目标函数 AST 子树，跳过注解/docstring/错误消息字符串；
  超上限按算子分层采样（种子化）；杀伤矩阵 `pytest -x` 进程池并行。
- **多信号验收门禁**：正确性、确定性（抗 flaky）、可证伪性；覆盖率增量默认只报告不强制（理由见报告 §4.3）。
- **实验框架**：B0–B5 六变体配对实验、18 目标确定性基准、手写 Wilcoxon/bootstrap 统计（零重依赖）、
  逐格落盘崩溃续跑、跨网格重复性检验与出图。
- **诚实的成本账目**：token 数恒精确；美元数只在配置了带来源的单价时出现，否则显示 n/a 而非假的 $0。
- **复现包**：`--preset published` 一条命令固化已发表网格参数，见 [REPRODUCE.md](REPRODUCE.md)。

## 用法速查

| 想做什么 | 命令 |
|---|---|
| 给基准函数生成并验收测试 | `testforge.cli run --target <id> --variant B3 --mode mock` |
| 在你自己的 `.py` 上跑 | `testforge.cli run --module 路径 --function 函数名 [--tests 已有测试]` |
| 换实验条件做对照 | `--variant B0`（仅既有套件）… `B5`（反馈不早退），定义见 `testforge/variants.py` |
| 跑已发表参数的完整网格 | `experiments/run_experiment.py --mode mock --preset published` |
| 统计分析 / 出图 | `experiments/analyze.py --exp <目录>` ／ `experiments/plots.py --exp <目录>` |
| 跨模型对比 | `experiments/analyze.py --exp <新网格> --compare-with <旧网格>` |
| 接真实 LLM 端点 | `.env` 配端点变量（见 [.env.example](.env.example)）＋ `--mode api` |

后端选择优先级：`--mode` 显式传参 > `TESTFORGE_MODE` 环境变量 > `mock`。
## 实验结果概览

真实 LLM（Qwen3-VL-8B，自建 vLLM）两轮独立采样完整网格（18 目标 × 5 变体，
`--preset published` 参数集），180 格零错误交叉验证；确定性 Mock 单轮 90 格用于机制对比。
产物提交在 `results/exp_*`，复核路径：本文数字 → `results/exp_*/analysis.md` → `results.json` 逐格。

| 后端 | 结论 | 值 |
|---|---|---|
| 真实 LLM | 生成把平均变异分数抬高 | 77.6% → 91.3%（B0 → B1） |
| 真实 LLM | 两轮独立采样网格配对提升 | **+12.7pp**（n=36，Wilcoxon p=0.0001，CI [+8.5, +17.2]，0 负） |
| 真实 LLM | 门禁把验收测试数减半而分数不降 | 1.28 → 0.61 个/目标，MS 同为 91.3% |
| 真实 LLM | 取消"零验收即早退"后的回路增量（B5 对 B2） | **+4.2pp**（n=36，p=0.0115，CI [+1.8, +7.1]，0 负） |
| 离线 Mock | 覆盖率与检出力解耦 | 无门禁多收测试：覆盖率 91.5% 对 87.2%，MS 同为 85.5% |
| 离线 Mock | 门禁按可证伪性拒掉的候选数 | 53 次，不采纳缺乏证据的测试 |

## 可复现性

| 层级 | 保证 | 验证 |
|---|---|---|
| 单元测试 | `python -m pytest` 全绿 | CI 四格矩阵 + 本地 |
| 单格运行（Mock） | 同命令重跑，JSON 除 `wall_sec` 外逐字段相同 | `cli run` 跑两遍比较 |
| 完整网格（Mock） | `--preset published` 重跑，指纹与均分复现已发表档案 | [REPRODUCE.md](REPRODUCE.md) 四步 |
| 真实 LLM 网格 | 方向、显著性、效应量可复现；单格分数受采样随机性影响 | 清缓存独立采样重跑 |

变异采样与 Mock 采样全部种子化（`zlib.crc32`，规避 `PYTHONHASHSEED`）；网格逐格落盘、崩溃续跑；
prompt 缓存命中时逐位重放，清空缓存即获得独立采样。

## 项目结构与文档

```text
testforge/           包本体：analysis / mutation / gate / llm / agent / report / cli / presets
benchmarks/          6 模块 × 18 目标函数 + 每模块刻意不完整的 B0 既有测试
experiments/         run_experiment 网格 / analyze 统计 / plots 出图 / compare_grids
tests/               70 个自身测试（11 个文件）
results/exp_*        实验产物（JSON/MD/PNG），只读不改
```

| 文档 | 内容 |
|---|---|
| [docs/report.md](docs/report.md) | 技术报告：方法、实验、统计、有效性威胁、后续工作 |
| [REPRODUCE.md](REPRODUCE.md) | 从 clone 到复现已发表数字的四步判据 |
| [docs/getting-started.md](docs/getting-started.md) | 上手手册：命令、参数、故障对照 |
| [CHANGELOG.md](CHANGELOG.md) / [AGENTS.md](AGENTS.md) | 版本变更 ／ 事实与约束（给贡献者与 AI 助手） |

## 本地验证

```bash
python -m pytest                                              # 70 项测试
python -m pyflakes testforge experiments tests conftest.py    # 静态检查，0 项
python experiments/run_experiment.py --mode mock --preset published --out results/exp_check
                                                              # 复现已发表 Mock 网格（约 1 小时）
```

## 已知边界

1. **Mock 不等于真实模型**：它是"先跑函数、把观测值冻成断言"的特征化生成器，杀得掉常量与算子类
   变异体，造不出需要语义理解的预言机；它验证机制，不主张生成质量。
2. **效果结论的模型覆盖**：v0.2 的效果结论来自 Qwen3-VL-8B 两轮网格；更大模型重跑在路线图上。
3. **基准规模与成本口径**：18 个确定性纯函数、单一语言（Python）；等价变异体无法穷尽排除，变异分数是下界；
   v0.1 归档的美元数来自无来源占位单价，一律按"未定价"处理。

## Roadmap

- [x] 0.2 复现包化：`--preset published` + REPRODUCE.md + 指纹验收
- [x] 0.2 成本口径诚实：无来源不出美元数
- [x] 门禁进 CI：Mock 全链路冒烟格（0.2 提前落地）＋ 手动触发的 `api-smoke`
- [ ] 0.3 外部效度：第二个模型（更大规模）重跑同网格
- [ ] 变异体优先级排序 / 增量变异执行 / property-based 生成扩展
## 贡献与许可

改动前请读 [AGENTS.md](AGENTS.md)（事实口径）与 [REPRODUCE.md](REPRODUCE.md)（验收判据）。
任何改动都要过三条门禁：`pytest` 全绿、`pyflakes` 0 项、`--preset published` Mock 网格指纹不变。
欢迎 issue / PR。许可证 [MIT](LICENSE)。

## 引用

```bibtex
@misc{testforge2026,
  author       = {Luz7818},
  title        = {TestForge: A Mutation-Guided Test Quality Agent},
  year         = {2026},
  howpublished = {\url{https://github.com/Luz7818/testforge}},
  note         = {Open-source end-to-end reproduction and paired study of
                  mutation-guided LLM test generation (Meta ACH, FSE 2025)}
}
```

## 致谢

Meta ACH（FSE 2025）与 TestGen-LLM（FSE 2024）；MutGen、PRIMG、MuTAP、GEM；DeMillo & Offutt 的变异测试理论及其工业实现 PIT / mutmut。
