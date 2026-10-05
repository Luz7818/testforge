# 给 AI 的项目说明

> 用途：给 AI 编码助手。这里是事实与约束，不含介绍性文字。改动本仓库前先读这份。
> README.md 与 docs/getting-started.md 里被引用的事实以本文件为准，它们只链接不复述。

## 一句话

一个 Python CLI + 实验框架：给一个函数，LLM 生成候选单元测试，只有稳定通过原代码、且至少杀死一个
“既有测试杀不死的变异体”的候选才被收进套件。离线 Mock 后端不联网即可跑完整条链路。

## 当前真实状态

以下都在本机 `.venv`（Python 3.12.0，复核：`.venv/Scripts/python.exe --version`）实测。

| 项 | 值 | 复核命令 |
|---|---|---|
| 测试数 | 91 个测试（全部收集成功） | `.venv/Scripts/python.exe -m pytest --collect-only`，末行 `91 tests collected` |
| 测试全通过 | 91 项通过，退出码 0（0.6 新增 PR 门禁/批处理/预算测试） | `.venv/Scripts/python.exe -m pytest` |
| 静态检查 | pyflakes 0 项；它已在 `[project.optional-dependencies].dev` 里，`pip install -e .[dev]` 即恢复 | `.venv/Scripts/python.exe -m pyflakes testforge experiments tests conftest.py` |
| CLI 可用 | 退出码 0，五个子命令 `targets` / `run` / `report` / `ci` / `batch`；`pip install testforge` 后有 `testforge` 命令 | `.venv/Scripts/python.exe -m testforge.cli --help` |
| 基准规模 | 18 个目标函数 / 6 个模块 | `.venv/Scripts/python.exe -m testforge.cli targets`（输出 18 行） |
| 变异体候选总数 | 197 个（未加上限时的全量） | `.venv/Scripts/python.exe -c "from testforge.benchmarks import load_targets; from testforge.analysis import inspect_target; from testforge.mutation import generate_mutants; print(sum(len(generate_mutants(inspect_target(s).module_source, s.function_name, max_mutants=10**6)) for s in load_targets()))"` |
| 离线单格 | `numeric.integer_sqrt` B3：MS 76.2%、gen 8、acc 2，49 秒 | `.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock` |
| Mock 可复现 | 同命令跑两遍，JSON 仅 `wall_sec` 不同 | 跑两遍到两个 `--out` 目录后逐字段比较 |
| CI | 5 个 job：4 格测试矩阵（ubuntu 3.10/3.11/3.12 + windows 3.12，`pip install -e .[dev]` + pytest + CLI 冒烟）、`mutation-loop-smoke`（pyflakes + 一格 Mock 全链路冒烟 + 结果断言）、`api-smoke`（仅手动触发，无密钥自动跳过）。**这里不写"最近一次是哪个提交"**——分支每推一次它就变，写进文档同一次提交里就作废了；当前分支 HEAD 的徽章为 `passing`（复核见右）。本机没有 `gh`，但徽章与 Actions 接口对**公开仓都免认证**；要提交号再用 `/actions/runs`（匿名限 60 次/小时/IP，别拿它轮询） | `python -c "import urllib.request as u;b=u.urlopen(u.Request('https://github.com/Luz7818/testforge/workflows/CI/badge.svg',headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read().decode();print('passing' in b)"` 应为 `True`；步骤读 `.github/workflows/ci.yml` |
| 运行时依赖 | 3 项：`pytest>=8.0`、`coverage>=7.4`、`openai>=1.30`；`matplotlib>=3.8` 在可选组 `plots`（只被 `experiments/plots.py` 用，出图才装） | 读 `pyproject.toml` 的 `[project] dependencies` 与 `[project.optional-dependencies]` |
| 依赖安装位置 | 仓库根 `pyproject.toml`，无 `requirements.txt`；`testforge` 已以 editable 装进 `.venv`（0.2 起），从任意 cwd 都能 `python -m testforge.cli` | `.venv/Scripts/python.exe -m pip list`（有 `testforge 0.2.0` 条目） |
| prompt 缓存 | `llm_cache/`（8B 时代）与 `llm_cache_27b_{full,rq2,full_rep,rq2_rep}/`（四轮网格各一，采样间隔离）；缓存键含 `TESTFORGE_EXTRA_BODY`（0.3 起），不同请求体设置不互串 | `python -c "import pathlib;print(len(list(pathlib.Path('llm_cache_27b_full').glob('*.json'))))"` |

## 仓库地图

目录树本身与「每个目录的入口在哪」见仓根 [目录说明.md](目录说明.md)，本节只留职责与隐藏约束，两边不重复列目录。

| 路径 | 职责 | 关键文件 |
|---|---|---|
| `testforge/cli.py` | 命令行入口 | `_cmd_run` 依次做：读配置 → 取变体 → 解析目标 → 跑 → 落盘；参数表见 `--help` |
| `testforge/budget.py` | 硬预算（墙钟/token） | `Budget.exhausted()`；共享实例 = 批内共享预算；耗尽时生成循环干净停止、联合评估照跑（`VariantResult.budget_exceeded`） |
| `testforge/diff_targets.py` | diff→改动函数 | `parse_diff`（统一 diff 新侧行号）+ `changed_functions`（AST 函数跨度求交）；纯删除不产目标 |
| `testforge/pr_gate.py` | PR 质量门禁流程 | `ci` 子命令：diff→目标→预算内逐目标跑→summary.md；退出码非 0 仅限基础设施错误（低分是信息不是失败） |
| `testforge/batch.py` | 整仓批量增强 | `batch` 子命令：扫描公开顶层函数→优先级队列（无测试优先→测试少→名字序）→共享预算逐目标→batch-summary.md |
| `testforge/config.py` | 全部旋钮 + 零依赖 `.env` 读取 | `_load_dotenv()`（模块顶层调用）、`ForgeConfig.from_env()`（缺 key 时 `SystemExit`） |
| `testforge/variants.py` | 实验条件 B0–B5 的定义 | `VARIANTS` 字典：`rounds` / `gate_enabled` / `feedback_mode` / `continue_on_zero_accept` |
| `testforge/mutation/engine.py` | 变异体生成与采样 | `priority=True` 时预算先填基线已执行行（PRIMG 式），默认关；`mutation/runner.py` 的 `covered_lines` 参数启用增量执行（未覆盖行免跑、结果恒等） |
| `testforge/types.py` | 共享数据结构 | `Outcome.killed_mutant`（非 PASS 即杀死）、`VariantResult.ms_all` / `ms_covered` 为派生属性 |
| `testforge/agent/` | 回路编排与 prompt | `orchestrator.py`（`run_target`：基线 → 变异 → 生成 → 门禁 → 联合评估）、`prompts.py`（`=== BLOCK ===` 结构） |
| `testforge/gate/` | 验收判定与原代码执行 | `gate.py`（`evaluate_candidate`）、`runner.py`（`run_tests_once` / `measure_coverage`）、`__init__.py` 里定义 `coverage_pct` |
| `testforge/mutation/` | 变异体生成与杀伤矩阵 | `operators.py`（7 类算子）、`engine.py`（拼接、语法校验、分层采样、编号）、`runner.py`（进程池 + `pytest -x`） |
| `testforge/llm/` | 两个后端 | `client.py`：`OpenAICompatClient`（`TESTFORGE_TRANSPORT`（sdk/urllib）双传输、磁盘缓存/重试/节流/记账）与 `MockLLMClient`（特征化生成） |
| `testforge/analysis/` | 目标函数静态解析 | `inspector.py`：签名、docstring、参数表、行号区间 |
| `testforge/report/` | Markdown 渲染 | `renderer.py`：`render_target_report` / `render_summary` |
| `testforge/utils.py` | 临时工作区、子进程、diff、JSON | `workspace()`（一次性目录，退出即删）、`run_cmd()`（超时返回 -9） |
| `benchmarks/` | 目标函数 + 每模块一份既有测试（B0） | `manifest.json` 是目标清单的唯一来源 |
| `experiments/` | 网格、统计、图、跨网格比较 | `run_experiment.py` / `analyze.py` / `plots.py` / `compare_grids.py` |
| `tests/` | 自身测试 | 13 个文件、91 项，见 `tests/README.md` |
| `results/` | 实验产物 | 只读。`.gitignore` 用白名单只放行 `results/exp_*` 里的 JSON/MD/PNG |

## 关键约定

1. **确定性用 `zlib.crc32`，不用内建 `hash()`**：`orchestrator._stable_hash` 给变异采样种子和候选
   去重哈希用。内建 `hash()` 对 `str` 按进程随机加盐（`PYTHONHASHSEED`），换一次进程就会挑到另一批
   变异体，网格结果不可复现。`llm/client.py` 里 Mock 的测试函数名后缀同样用 crc32。
2. **prompt 磁盘缓存**：`OpenAICompatClient._cache_path` 用 `sha256(model|system|prompt|temperature|max_tokens|extra_body)`
   作键名写到 `llm_cache/`（或 `TESTFORGE_CACHE_DIR`）。命中即 `cached=True`、零 API 消耗、逐位重放。
   要一次独立采样就把缓存目录指到空目录（已发表的两轮真实网格即如此）。Mock 后端不读写缓存。
3. **逐格落盘、可续跑**：`run_experiment.py` 每跑完一个（目标 × 变体）就把整份 `results.json` 重写一次。
   重启时已完成格打印 `skip ... (cached)`；带 `error` 键的格会被移出 `results.json` 归档到同目录
   `errors.json` 后重跑（`results/exp_api27b_full/errors.json` 就是这么来的——首跑 36 格撞网关 420 限流后靠续跑补齐）。
4. **变异体分层采样上限**：候选超过 `max_mutants`（默认 24）时按算子分组轮转取样，组内用种子洗牌，
   目的是保住算子多样性而不是取前 N 个。每格种子 = `mutation_seed + crc32(target_id) % 10000`，
   所以换个 target_id 就会挑到不同的子集。编号 `M001…` 在采样之后按行号重排，换上限即换编号。
5. **B0 是模块级的**：一个模块的整份测试文件会同时用于该模块下三个目标函数，所以“既有套件”对
   同模块的三个目标是同一份。
6. **早退规则**：B3 在某轮零验收时退出（`accepted_this_round == 0 and not continue_on_zero_accept`），
   B5 唯一差别是把轮次预算走完。改这条规则会直接改动 RQ5 的对照定义。
7. **杀伤口径**：`classify_rc` 把 pytest 退出码 0 和 5 都算 PASS（5 是一个用例都没收集，靠可证伪性
   门禁把它挡在外面），1 为 FAIL，-9 为 TIMEOUT；TIMEOUT 计为杀死。候选是否被验收看的是
   `falsifiable`（至少杀一个存活变异体），不是覆盖率。
8. **`n_accepted` 是最终套件里的文件数**：联合评估若整体不通过，会按“和 B0 一起跑不过”逐个剔除，
   最多三轮。所以 `n_accepted` 可能小于回路中验收过的数量。
9. **数字口径**：README 与 `docs/report.md` 里的“36 个单元”“pooled n=36”指实验格数
   （18 目标 × 2 轮网格），不是测试数。测试数是 91，两处不要互相引用。

## 改动后的验证

| 你动了 | 必须跑 |
|---|---|
| `testforge/**` 任意文件 | `.venv/Scripts/python.exe -m pytest`（83 项通过，约 2.5 分钟） |
| `mutation/operators.py` / `engine.py` | `.venv/Scripts/python.exe -m pytest tests/test_operators.py tests/test_engine.py`；再核对上面那条 197 的计数是否变化 |
| `gate/` | `.venv/Scripts/python.exe -m pytest tests/test_gate.py` |
| `agent/orchestrator.py` / `llm/client.py` | `.venv/Scripts/python.exe -m pytest tests/test_e2e.py tests/test_mock_client.py`，再跑一次离线单格看 MS 是否漂移 |
| `config.py` / `.env` 读取逻辑 | `.venv/Scripts/python.exe -m pytest tests/test_dotenv.py tests/test_config_client.py tests/test_cost_accounting.py` |
| `benchmarks/` | `.venv/Scripts/python.exe -m pytest tests/test_inspector.py`（内含“18 个目标”的断言）+ `.venv/Scripts/python.exe -m testforge.cli targets` |
| `cli.py` 参数 | `.venv/Scripts/python.exe -m testforge.cli --help` 与 `run --help`，并至少执行一次离线单格 |
| `experiments/` | 冒烟网格（见 `experiments/README.md`）→ `analyze.py` → `plots.py`，全部指向临时目录 |
| 任一文档 | `cd ../文档标准 && python check_docs.py testforge` |

## 已知坑

- 本地 `.env` 现已配置 SEU 校园网关（`https://openapi.seu.edu.cn/v1`，模型 `qwen3.8-27b`，0.3 网格的
  真实后端；`TESTFORGE_TRANSPORT=urllib`、`TESTFORGE_EXTRA_BODY={"chat_template_kwargs": {"enable_thinking": false}}`、
  `TESTFORGE_MIN_CALL_INTERVAL_SEC=3`）。该文件不入库；换机器要重配，或只跑 Mock。`DEEPSEEK_API_KEY` 为空时
  `--mode api` 在建客户端之前就退出（退出码 1），不会带着空凭据发请求，这是设计行为。
- 该网关有两层拦截，都实测过：(a) WAF 对 openai SDK 的 HTTP 栈（httpx2）返回 HTML「禁止访问」页，
  curl/urllib 正常——所以 0.3 网格用 `TESTFORGE_TRANSPORT=urllib`；(b) 持续高频请求触发 HTTP 420
  压力限流——27B 主网格首跑因此丢过 36 格，靠「重跑同一命令只补错误格」的续跑机制 + 10 秒节流补齐。
  长限流窗口不要指望进程内重试，等窗口过去再续跑。
- `TESTFORGE_MODE` 从 0.2 起对 CLI 与网格脚本生效：`--mode` 缺省时取该环境变量，再退回 `mock`。
- 已发表的真实 LLM 网格全部来自 **qwen3.8-27B**（v0.4 起单模型口径）：主网格 `exp_api27b_full` +
  `exp_api27b_replicate`（16/3/2/×3，两采样），B5 网格 `exp_api27b_rq2full` + `exp_api27b_rq2full_rep`
  （24/4/4/×5，两采样），共 288 格零错误；Mock 网格 `exp_mock_full` 与模型无关。0.2 起用 `--preset published`
  / `--preset published-b5` 固化；指纹见 `testforge/presets.py`，复跑验收见 REPRODUCE.md。
  v0.1–v0.3 的 Qwen3-VL-8B 网格（`exp_api_*`）已撤出工作树，完整归档在 tag v0.3.0。
- `results/exp_mock_full/` 的 `analysis.md` 是旧脚本产物（缺两节），当前脚本的重算结果在
  同目录 `analysis_v2.md` / `analysis_v2.json`（旧文件未动）。重算版把 v0.1 占位单价算出的
  美元列按“未定价”处理，只保留精确 token 数。
- 仓库的 `addopts` 已含 `-q`，再敲 `-q` 就变成 `-qq`，只打印一行圆点、看不到通过数。要数字行就用
  `.venv/Scripts/python.exe -m pytest`。
- `plots.py` 的标题标签取自 `cost.model`。Mock 运行里 `cfg.model` 仍是默认 `deepseek-chat`，所以
  mock 网格的热力图标题会写成 `LLM: deepseek-chat`；跑 mock 网格时显式传 `--label "mock grid"`。
- 两个 `--out` 参数（CLI 与 `run_experiment.py`）都以仓库根为基准拼接，不是当前工作目录。
  0.2 起本包已 editable 安装，从非仓库根跑 `python -m testforge.cli` 不再依赖 cwd；`--module`
  这类用户文件路径仍按 cwd 解析。
- `results/` 下只有 `exp_*` 目录的 JSON/MD/PNG 被 git 跟踪；`results/demo/`、`results/demo_owncode/`、
  `results/api_smoke/`、`results/*.log` 是本机历史运行残留，新克隆的仓库里没有。
  `docs/example-report.md` 就是 `results/api_smoke/numeric.integer_sqrt__B3.json` 的渲染结果，
  克隆后无法重跑该核对。
- `docs/report.md` 末尾“36 个自测”与 `docs/interview.md` 的“全管线 36 个自测通过”是旧数字（现为 83）。
  这两份按要求保持原样，引用测试数时以本文件为准。
- 加一个新目标函数会让 `tests/test_inspector.py` 里“18 个目标”的断言失败——那是有意的登记闸门，
  改基准就要同时改断言。
- `.ruff_cache/` 是外部 ruff 运行留下的，`.venv` 里没有 ruff；本仓库能跑的静态检查是 pyflakes。

## 不要做的事

- 不要改 `results/` 下任何已提交产物来“让数字对得上”。要更新数字就重跑实验到新目录，再改文档引用。
- 不要手改 `llm_cache/` 里的缓存文件名或内容：文件名就是 prompt 指纹，改了就等于换 prompt。
- 不要把 `falsifiable` 门禁放宽成“覆盖率有提升就行”，也不要把 `coverage_delta` 设成默认强制——
  这两条是本项目与 TestGen-LLM 式验收的差别所在，`docs/report.md` §4.3 记了理由。
- 不要把 `zlib.crc32` 换成内建 `hash()`（`orchestrator.py` 的两处、`llm/client.py` 里 Mock 的测试名
  后缀）：内建 hash 按进程加盐，换一次进程就换一批变异体，历史网格全部失去可比性。
- 不要在 README 与手册里另写一套数字。测试数、命令、路径的口径改到本文件。
- CI 只做安装校验、测试、CLI 冒烟、pyflakes 与一格 Mock 全链路冒烟（`mutation-loop-smoke`），
  外加一个需手动触发、未配置密钥或未显式 opt-in（`TESTFORGE_SMOKE_ENABLED=1`）时自动跳过的 `api-smoke`；
  不要往里加打包/发布流水线。
