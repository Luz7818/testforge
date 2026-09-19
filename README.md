# TestForge — 变异测试引导的 AI 测试质量智能体

![CI](https://github.com/Luz7818/testforge/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

**LLM 生成的单元测试"能通过"，不等于"能抓住 Bug"。TestForge 用变异测试（mutation testing）作为验收标准，构建了一个生成→门禁→反馈→验收的闭环智能体，让 AI 测试的质量变得可证明、可量化、可审计。**

> *Generated tests that pass are not tests that catch bugs. TestForge is an agent loop that only accepts AI-written tests that provably kill seeded faults — an open-source reproduction and extension of Meta's ACH (FSE 2025).*

> 面向面试的完整工程项目：真实工业痛点 + 顶会论文背书（Meta ACH, FSE 2025）+ 可复现实验 + 严格统计检验。
> 技术报告见 [docs/report.md](docs/report.md)，面试准备手册见 [docs/interview.md](docs/interview.md)。

---

## 1. 问题：AI 生成的测试为什么不可信

2026 年，AI 编程助手最大的痛点已经从"能不能写代码"变成"**产出看似正确但实际不可信**"：

- 66% 的企业用户反映 AI 代码"几乎对但差一点"（[Kilo 2026 Buyer's Guide](https://kilo.ai)），AI 辅助代码的评审返工率显著上升（[Glean](https://www.glean.com)）；
- 在测试生成场景，这个问题更隐蔽：LLM 针对当前代码写测试，生成的测试**天然倾向于通过**——断言薄弱、边界缺失、只覆盖执行路径不校验行为。行覆盖率好看，但测试杀死不了任何被植入的缺陷（mutant）；
- **"测试通过"验证的是代码与测试互相一致，而不是代码正确。** 没有故障检出能力（fault detection capability）度量的测试生成，是在优化一个错误的代理指标。

工业界已经行动：Meta 在 FSE 2025 发表 [ACH 系统](https://arxiv.org/abs/2506.02954)（*Mutation-Guided LLM-based Test Generation at Meta*），用变异测试反馈驱动 LLM 生成更强的测试；学界有 MutGen（arXiv 2025）、PRIMG、MuTAP 等后续工作。**但目前没有开源、端到端、带严格评估的完整实现。** TestForge 补上这一环。

## 2. 方案：把"质量"做成门禁，把"漏洞"变成反馈

```mermaid
flowchart LR
    IN["目标函数<br/>module + B0 测试"] --> SA["静态分析<br/>AST 签名/文档/行号"]
    SA --> GEN["LLM 生成<br/>K 候选 / 轮"]
    GEN --> GATE{"质量门禁"}
    GATE -->|"拒绝"| FB["存活变异体<br/>最小语义 diff"]
    FB -->|"反馈强化"| GEN
    GATE -->|"有证据才验收"| ACC["验收合并"]
    ACC --> OUT["测试套件<br/>报告 + 成本账单"]
    MUT["变异引擎<br/>7 算子 · 杀伤矩阵并行"] -.->|"杀伤归因"| GATE
    MUT -.->|"存活集合"| FB
    classDef llm fill:#e3f2fd,stroke:#5b8db8,color:#0d47a1;
    classDef mut fill:#fff3e0,stroke:#e2b93b,color:#795548;
    classDef agent fill:#e8f5e9,stroke:#4c8f5c,color:#1b5e20;
    class GEN,FB llm;
    class MUT mut;
    class SA,GATE,ACC,OUT,IN agent;
```

**质量门禁（全过才验收）**

| 信号 | 含义 | 拒绝什么样的测试 |
|---|---|---|
| `runs_on_original` | 在当前代码上重复通过 N 次 | 一次过的侥幸测试、随机器/时间导致的 flaky 测试 |
| `falsifiable` | 至少杀死 1 个"存活变异体" | 断言空洞、只跑不改的表演型测试 |
| `coverage_delta`（可选） | 新增覆盖行 | 纯重复既有覆盖的测试（默认仅报告不强制，见报告 §4.3） |

**变异体反馈回路**：门禁拒绝后，把"你的测试没抓到的种子缺陷"以最小 diff 形式回填给模型：

```
[M008] line 17 (CRN): `i + 1` -> `i + 2`
```

模型看到的是精确的语义变化，而不是模糊的"写得更好一点"——这是与 Meta ACH 一致的核心机制。

## 3. 快速开始

```bash
# 环境（Windows / macOS / Linux 通用，Python ≥ 3.10；从仓库根目录运行，免安装）
python -m venv .venv
.venv/Scripts/pip install pytest coverage openai matplotlib   # Linux/macOS: .venv/bin/pip
# 注：若项目路径含非 ASCII 字符，`pip install -e .` 可能因 setuptools 路径编码问题失败；
#     本项目无需安装即可运行（仓库根目录直接 python -m ...）。

# ① 离线体验全流程（Mock 模式，零 API 成本）
.venv/Scripts/python -m testforge.cli targets                     # 查看 18 个基准目标
.venv/Scripts/python -m testforge.cli run --target parsers.parse_csv_line --variant B3 --mode mock
.venv/Scripts/python -m testforge.cli report --results results/demo/parsers.parse_csv_line__B3.json --out report.md

# ② 真实 LLM 实验（DeepSeek，OpenAI 兼容接口）
cp .env.example .env        # 填入 DEEPSEEK_API_KEY
.venv/Scripts/python experiments/run_experiment.py --mode api         # 全网格：18 目标 × 5 变体
.venv/Scripts/python experiments/analyze.py --exp results/exp_api_<stamp>   # 统计检验 + RQ 分析
.venv/Scripts/python experiments/plots.py   --exp results/exp_api_<stamp>   # 图表

# ③ TestForge 自身测试（29 个）
.venv/Scripts/python -m pytest tests/ -q
```

变体说明（实验网格的每一列）：

| 变体 | 生成 | 门禁 | 反馈回路 | 对应研究问题 |
|---|---|---|---|---|
| **B0** | — | — | — | 既有测试套件基线 |
| **B1** | 单次 | ✗ | ✗ | "氛围测试"现状（RQ1/RQ2/RQ3 基线） |
| **B2** | 单次 | ✓ | ✗ | 门禁的独立贡献（RQ3） |
| **B3** | 多轮 | ✓ | 存活变异体 diff | **完整方案（ours）**（RQ2） |
| **B4** | 多轮 | ✓ | 覆盖缺口 | 消融：反馈信号换成覆盖率（RQ4） |

## 4. 目录结构

```
testforge/
├── testforge/                 # 主包
│   ├── analysis/inspector.py  #   AST 静态分析：签名/注解/文档/行号区间
│   ├── llm/client.py          #   DeepSeek(OpenAI兼容) + 确定性 Mock 双后端；缓存/重试/记账
│   ├── mutation/operators.py  #   7 类 AST 变异算子（AOR/ROR/BCR/CRN/CRS/UOR/RTN）
│   ├── mutation/engine.py     #   变异体生成：源码拼接/校验/分层采样
│   ├── mutation/runner.py     #   杀伤矩阵执行：进程池并行 + pytest -x 提前退出
│   ├── gate/gate.py           #   质量门禁：正确性/flaky/可证伪/覆盖率增量
│   ├── gate/runner.py         #   子进程测试执行 + coverage 精确测量
│   ├── agent/orchestrator.py  #   编排器：生成→门禁→反馈→验收→联合评估
│   ├── agent/prompts.py       #   结构化 Prompt（初始 + 变异反馈 + 修复）
│   ├── report/renderer.py     #   Markdown 报告
│   └── cli.py                 #   命令行入口
├── benchmarks/                # 6 模块 × 18 目标函数 + B0 既有测试
├── experiments/               # 实验网格 / 统计分析 / 图表
├── tests/                     # TestForge 自身测试（29 个）
├── docs/report.md             # 技术报告（问题/相关工作/设计/实验/局限）
└── docs/interview.md          # 面试手册（电梯稿/STAR/追问 Q&A）
```

## 5. 工程亮点（面试讨论点）

- **杀伤矩阵的执行工程**：O(测试×变异体) 次测试执行，通过进程池并行 + `pytest -x` 首败即停 + 仅对存活变异体执行候选测试三个手段压成本；TIMEOUT 按惯例计为杀死（行为改变的观察）。
- **成本工程**：prompt 磁盘缓存（同 prompt 重跑零 API 成本）、单次响应携带 K 个候选、token/费用逐笔记账、变异体分层采样上限。
- **可复现性**：变异采样与 Mock 输入采样全部种子化（crc32 而非内置 hash，规避 PYTHONHASHSEED 随机化）；LLM 响应缓存；每格实验崩溃安全的增量落盘。
- **诚实工程**：Mock 模式是真实的"特征化测试"生成器（捕获-重放），能杀掉大量值/算子类变异体但**不会伪装**杀掉需要语义理解的变异体——门禁会诚实地拒绝它，演示了系统不是靠作弊达标。
- **测试系统本身**：29 个单元/集成测试覆盖算子、拼接、门禁、Mock 确定性、杀伤矩阵与端到端管线，由 GitHub Actions 在 ubuntu（3.10/3.11/3.12）+ windows（3.12）矩阵上持续验证，并通过 `pip install -e .` 校验打包配置。

## 6. 结果快照（Mock 全网格，90/90 格零错误）

| 全网格一览（18 目标 × 5 变体） | 变体均值对比 |
|---|---|
| ![heatmap](results/exp_mock_full/plots/ms_heatmap.png) | ![bar](results/exp_mock_full/plots/ms_by_variant.png) |

> 完整分析与统计检验见 [results/exp_mock_full/analysis.md](results/exp_mock_full/analysis.md)。

- **生成有效**：单次生成（B1）相对既有套件（B0）变异分数 **+7.8pp**（9 胜/9 平/0 负，Wilcoxon p=0.0076，bootstrap 95% CI [+4.0, +11.8]）；
- **门禁反冗余**：B1 与 B2/B3 变异分数相同（85.5%），但验收测试数 2.50 → 0.56/目标（**4.5× 更少**）；B1 冗余测试推高覆盖率 4.3pp 却零检出增益——**覆盖率与故障检出力的解耦实证**；
- **诚实平台期**：Mock 杀不动的存活变异体（如引号转义边界）被门禁全部拒绝（53 次 `falsifiable` 拒绝），系统不在无法证明价值时声称价值——这正是留给真实 LLM 反馈回路的区间（`--mode api` 一键复现）。

**验收测试长什么样**（`numeric.integer_sqrt` 的真实生成产物，Mock 运行）：

```python
import pytest
from numeric import integer_sqrt


def test_integer_sqrt_16089():
    assert integer_sqrt(0) == 0


def test_integer_sqrt_11030():
    assert integer_sqrt(3) == 1


def test_integer_sqrt_42941():
    assert integer_sqrt(100) == 10
```

三个边界断言各杀死一个 B0 杀不死的变异体，使该目标的变异分数从 56% 提升到 75%：`integer_sqrt(0) == 0` 抓住 `if n < 0` 的 `0 → 1` 常量变异（变异后对 0 抛 ValueError）与 `n < 2` 分支的 `return n → return None`；`integer_sqrt(3) == 1` 抓住二分初始化 `lo, hi = 1, ...` 的 `lo = 1 → 2` 常量变异（变异后 `integer_sqrt(3)` 返回 2）。

## 7. 引用与依据

- Meta, *Mutation-Guided LLM-based Test Generation at Meta*（ACH）, FSE 2025；Meta 工程博客 *LLMs Are the Key to Mutation Testing*（2025-09）
- MutGen: *Mutation-Guided Unit Test Generation with a Large Language Model*, arXiv:2506.02954
- PRIMG: *Efficient LLM-driven Test Generation Using Mutant Prioritization*, 2025
- Meta, *TestGen-LLM: Automatically Improving Unit Tests using Large Language Models*, FSE 2024（验收式测试增强范式）
- 行业痛点数据：Kilo 2026 Buyer's Guide；Glean 企业 AI 效能报告（2026）

## 8. License

MIT
