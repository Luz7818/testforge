# AGENTS.md —— 项目协作与代码开发规范（唯一权威入口）

> 用途：给 AI 编码助手与所有开发者。这里是规范入口与索引：目标、原则、流程、模块规则、
> 维护矩阵、阅读清单都在这份文件里。细则一律链接到对应文件，冲突时以细则文件为准并回改本文件。
> README.md 与 docs/GET-START.md 里被引用的事实以本文件的「当前状态」为准，它们只链接不复述。

## 项目目标

- 定位：Python CLI + 实验框架：给一个函数，LLM 生成候选单元测试，只有稳定通过原代码、且至少
  杀死一个"既有测试杀不死的变异体"的候选才被收进套件。离线 Mock 后端不联网即可跑完整条链路。
- 核心功能：变异引导测试生成（B0–B5 六变体配对实验）、18 目标确定性基准、PR 质量门禁
  （`testforge ci`）、整仓批量增强（`testforge batch`）、仓库即 GitHub Action。
- 技术栈：Python 3.10–3.12，运行时依赖 `pytest`/`coverage`/`openai`（复核：`pip list`）。
- 详情：[README.md](README.md)、[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 开发原则

1. 正确性优先。
2. 可维护性优先。
3. 代码简洁、项目简洁。
4. 小步迭代。
5. 单模块开发。
6. 每个改动必须有明确设计与验收标准。
7. 禁止一次生成整个项目。
8. 禁止跳步开发。

执行口径：先想后写（假设与歧义先挑明）；最简优先（不加没要求的功能与抽象——统计与 `.env`
解析都是手写 stdlib 实现，不为省事引依赖）；外科手术式改动（不动无关代码，每行改动可追溯到
需求）；目标驱动（先有可验证判据再动手，宣称完成前先跑通 [docs/TESTING.md](docs/TESTING.md)
的门禁）。

## 开发流程

**分析 → 设计 → 实现 → 测试 → 文档更新 → Git提交 → 等待确认**。不得跳过任何阶段。

| 阶段 | 产出物 | 放行标准 |
|---|---|---|
| 分析 | 影响面清单（回路/变异/门禁/后端/实验哪一侧） | 影响面说全 |
| 设计 | 方案说明（口径与默认值变化、对已发表网格的影响） | 验收标准已定义；与更简方案比较过 |
| 实现 | 代码 | 只含设计内改动，符合 [docs/CODE-STYLE.md](docs/CODE-STYLE.md) |
| 测试 | 门禁结果 | [docs/TESTING.md](docs/TESTING.md) 全过（pytest + pyflakes + 离线单格） |
| 文档更新 | 受影响文档 diff | 维护矩阵逐项过完 |
| Git提交 | 提交 | 符合 [docs/GIT.md](docs/GIT.md)，一批一提交 |
| 等待确认 | —— | 等人确认后推送 |

## 模块开发规则

- 一个智能体一次只开发一个模块；模块完成后才能进入下一模块。
- 如需同时开发，使用多个子智能体，每个子智能体同样一次只开发一个模块。

模块完成标准（全部满足才算完成）：

1. 功能完成：达到 [TODO.md](TODO.md) 中该任务的验收标准。
2. 测试通过：符合 [docs/TESTING.md](docs/TESTING.md)。
3. 最简原则：代码和项目架构都保持最简洁，无冗余抽象与重复实现。
4. [TODO.md](TODO.md) 更新：勾选完成项、明确下一项。
5. [HISTORY.md](HISTORY.md) 追加变更记录（破坏 CLI/config 契约升 major，新增能力升 minor）。
6. 受影响的 docs 更新（按需）。
7. [README.md](README.md) 更新（如有面向使用者的变化）。
8. Commit message 符合 [docs/GIT.md](docs/GIT.md)。

## 文档维护规则

| 事件 | 需更新 |
|---|---|
| 模块完成 | `TODO.md`、`HISTORY.md`、受影响 docs |
| 版本发布 | `HISTORY.md` 新条目 + `testforge/__init__.py` 版本号 + tag |
| 架构决策（口径、默认值、缓存键、门禁规则变化） | `docs/ARCHITECTURE.md` + `HISTORY.md` 记录缘由 |
| 命令/入口/参数变化 | `README.md` / `docs/GET-START.md` / 对应子目录 README |
| 增删一级或二级目录 | 仓根 `目录说明.md` + 本文件 |
| 测试数/基准规模/CI 变化 | 本文件「当前状态」 |
| 新对话/新任务开始 | 按下方阅读清单阅读 |

## 开发前阅读清单

每个新对话/新任务，按顺序阅读：

1. 本文件（`AGENTS.md`）
2. [TODO.md](TODO.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)（模块职责表与 9 条关键约定在这里）
4. [docs/GET-START.md](docs/GET-START.md)
5. [HISTORY.md](HISTORY.md)
6. 与任务相关的 [docs/CODE-STYLE.md](docs/CODE-STYLE.md)、[docs/TESTING.md](docs/TESTING.md)、[docs/GIT.md](docs/GIT.md)

阅读完成后**不要写代码**：先做架构评审，输出——项目理解 / 核心模块 / 模块依赖关系 / 潜在风险 /
建议优化项 / 推荐开发顺序 / 是否发现架构问题——然后等待确认。

- 工作区级纪律不在本清单里：新增/摆放文件与目录先读 `../文档标准/项目整体规范.md` §2.3（最小根判断顺序）；跨仓耦合与 Git 纪律见其 §八。
## Git 索引

- Git 规范：[docs/GIT.md](docs/GIT.md)（results 白名单、llm_cache 边界、CI 构成、一批一提交）

## 当前状态

以下都在本机 `.venv`（Python 3.12.0，复核：`.venv/Scripts/python.exe --version`）实测。

| 项 | 值 | 复核命令 |
|---|---|---|
| 测试数 | 89 个测试（全部收集成功） | `.venv/Scripts/python.exe -m pytest --collect-only`，末行 `89 tests collected` |
| 测试全通过 | 89 项通过，退出码 0（0.6 新增 PR 门禁/批处理/预算测试；2026-10-07 删 presets 死函数连带 2 项） | `.venv/Scripts/python.exe -m pytest` |
| 静态检查 | pyflakes 0 项；它已在 `[project.optional-dependencies].dev` 里，`pip install -e .[dev]` 即恢复 | `.venv/Scripts/python.exe -m pyflakes testforge experiments tests` |
| CLI 可用 | 退出码 0，五个子命令 `targets` / `run` / `report` / `ci` / `batch`；`pip install testforge` 后有 `testforge` 命令 | `.venv/Scripts/python.exe -m testforge.cli --help` |
| 基准规模 | 18 个目标函数 / 6 个模块 | `.venv/Scripts/python.exe -m testforge.cli targets`（输出 18 行） |
| 变异体候选总数 | 197 个（未加上限时的全量） | `.venv/Scripts/python.exe -c "from testforge.benchmarks import load_targets; from testforge.analysis import inspect_target; from testforge.mutation import generate_mutants; print(sum(len(generate_mutants(inspect_target(s).module_source, s.function_name, max_mutants=10**6)) for s in load_targets()))"` |
| 离线单格 | `numeric.integer_sqrt` B3：MS 76.2%、gen 8、acc 2，49 秒 | `.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock` |
| Mock 可复现 | 同命令跑两遍，JSON 仅 `wall_sec` 不同 | 跑两遍到两个 `--out` 目录后逐字段比较 |
| CI | 5 个 job：4 格测试矩阵（ubuntu 3.10/3.11/3.12 + windows 3.12，`pip install -e .[dev]` + pytest + CLI 冒烟）、`mutation-loop-smoke`（pyflakes + 一格 Mock 全链路冒烟 + 结果断言）、`api-smoke`（仅手动触发，无密钥自动跳过）。**这里不写"最近一次是哪个提交"**——分支每推一次它就变，写进文档同一次提交里就作废了；当前分支 HEAD 的徽章为 `passing`（复核见右）。本机没有 `gh`，但徽章与 Actions 接口对**公开仓都免认证**；要提交号再用 `/actions/runs`（匿名限 60 次/小时/IP，别拿它轮询） | `python -c "import urllib.request as u;b=u.urlopen(u.Request('https://github.com/Luz7818/testforge/workflows/CI/badge.svg',headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read().decode();print('passing' in b)"` 应为 `True`；步骤读 `.github/workflows/ci.yml` |
| 运行时依赖 | 3 项：`pytest>=8.0`、`coverage>=7.4`、`openai>=1.30`；`matplotlib>=3.8` 在可选组 `plots`（只被 `experiments/plots.py` 用，出图才装） | 读 `pyproject.toml` 的 `[project] dependencies` 与 `[project.optional-dependencies]` |
| 依赖安装位置 | 仓库根 `pyproject.toml`，无 `requirements.txt`；`testforge` 已以 editable 装进 `.venv`（0.5 起），从任意 cwd 都能 `python -m testforge.cli`（editable 元数据落后源码的 `0.6.0` 一版，重装即同步） | `.venv/Scripts/python.exe -m pip list`（有 `testforge 0.5.0` 条目） |
| prompt 缓存 | `llm_cache/` 根部 = 默认缓存；其下五个子目录 `27b_full`、`27b_full_rep`、`27b_rq2_rep`、`rq2_rep`、`rq2full_rep` = 历次真实网格的独立采样缓存（2026-10-05 从根部散目录收拢，采样间隔离）；缓存键含 `TESTFORGE_EXTRA_BODY`（0.3 起），不同请求体设置不互串 | `python -c "import pathlib;print(len(list(pathlib.Path('llm_cache/27b_full').glob('*.json'))))"` |

## 已知坑（省下一次的调查时间）

- 本地 `.env` 配置 SEU 校园网关（不入库；换机器重配或只跑 Mock）。`DEEPSEEK_API_KEY` 为空时
  `--mode api` 在建客户端之前就退出（退出码 1），设计行为。
- 该网关两层拦截（都实测过）：(a) WAF 对 openai SDK 的 httpx2 返回 HTML 拦截页，curl/urllib
  正常——用 `TESTFORGE_TRANSPORT=urllib`；(b) 高频请求触发 HTTP 420 限流——靠续跑机制 +
  `TESTFORGE_MIN_CALL_INTERVAL_SEC` 节流补齐；长限流窗口等它过去再续跑。
- `TESTFORGE_MODE` 从 0.2 起对 CLI 与网格脚本生效：`--mode` 缺省时取该环境变量，再退回 `mock`。
- 已发表真实 LLM 网格全部来自 **qwen3.8-27B**（v0.4 起单模型口径）：288 格零错误；0.2 起
  `--preset published` / `--preset published-b5` 固化；v0.1–v0.3 的 8B 网格归档在 tag v0.3.0。
- `results/exp_mock_full/analysis.md` 是旧脚本产物（缺两节），重算版在同目录 `analysis_v2.md`；
  重算版把 v0.1 占位单价算出的美元列按"未定价"处理。
- `results/` 下只有 `exp_*` 的 JSON/MD/PNG 与 `results/README.md` 被跟踪；`demo/`、`api_smoke/` 已删除，`*.log` 不会入库。
  `docs/example-report.md` 来自已跟踪的 `results/exp_api27b_smoke/`（`results.json` + `summary.md`）渲染。
- `docs/report.md` 末尾"36 个自测"与 `docs/interview.md` 的"全管线 36 个自测通过"是旧数字
  （现为 89）。这两份按要求保持原样，引用测试数以本文件为准。
- `.ruff_cache/` 是外部 ruff 运行留下的；本仓能跑的静态检查是 pyflakes。
- `--out` 参数以仓库根为基准拼接，不是当前工作目录；`--module` 这类用户文件路径仍按 cwd 解析。
- `plots.py` 标题取自 `cost.model`，mock 网格会写 `LLM: deepseek-chat`——跑 mock 网格显式传
  `--label "mock grid"`。
- 不要改 `results/` 已提交产物来"让数字对得上"；不要手改 `llm_cache/`；不要放宽 `falsifiable`
  门禁或把 `coverage_delta` 设为默认强制；不要把 `zlib.crc32` 换成内建 `hash()`；不要在
  README 与手册里另写一套数字；不要往 CI 加打包/发布流水线。
