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
| 测试数 | 49 个测试（全部收集成功） | `.venv/Scripts/python.exe -m pytest --collect-only`，末行 `49 tests collected` |
| 测试全通过 | 49 项通过，退出码 0，末行 `49 passed`（本机两次实测 46.5 秒与 45.7 秒） | `.venv/Scripts/python.exe -m pytest` |
| 静态检查 | pyflakes 0 项（它未写进依赖清单，是 `.venv` 里现成的开发工具） | `.venv/Scripts/python.exe -m pyflakes testforge experiments tests conftest.py` |
| CLI 可用 | 退出码 0，三个子命令 `targets` / `run` / `report` | `.venv/Scripts/python.exe -m testforge.cli --help` |
| 基准规模 | 18 个目标函数 / 6 个模块 | `.venv/Scripts/python.exe -m testforge.cli targets`（输出 18 行） |
| 变异体候选总数 | 197 个（未加上限时的全量） | `.venv/Scripts/python.exe -c "from testforge.benchmarks import load_targets; from testforge.analysis import inspect_target; from testforge.mutation import generate_mutants; print(sum(len(generate_mutants(inspect_target(s).module_source, s.function_name, max_mutants=10**6)) for s in load_targets()))"` |
| 离线单格 | `numeric.integer_sqrt` B3：MS 76.2%、gen 8、acc 2，49 秒 | `.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock` |
| Mock 可复现 | 同命令跑两遍，JSON 仅 `wall_sec` 不同 | 跑两遍到两个 `--out` 目录后逐字段比较 |
| CI | 4 格矩阵：ubuntu 3.10/3.11/3.12 + windows 3.12；步骤为 `pip install -e .`、`python -m pytest tests/ -q`、`cli targets`、`cli --version` | 读 `.github/workflows/ci.yml` |
| 运行时依赖 | 4 项：`pytest>=8.0`、`coverage>=7.4`、`openai>=1.30`、`matplotlib>=3.8` | 读 `pyproject.toml` 的 `[project] dependencies` |
| 依赖安装位置 | 仓库根 `pyproject.toml`，无 `requirements.txt`；`testforge` 本身未装进 `.venv` | `.venv/Scripts/python.exe -m pip list`（查不到 testforge 条目） |
| prompt 缓存 | 本机 `llm_cache/` 78 个 JSON（`--mode api` 才会写） | `.venv/Scripts/python.exe -c "import pathlib;print(len(list(pathlib.Path('llm_cache').glob('*.json'))))"` |

## 仓库地图

| 路径 | 职责 | 关键文件 |
|---|---|---|
| `testforge/cli.py` | 命令行入口 | `_cmd_run` 依次做：读配置 → 取变体 → 解析目标 → 跑 → 落盘；参数表见 `--help` |
| `testforge/config.py` | 全部旋钮 + 零依赖 `.env` 读取 | `_load_dotenv()`（模块顶层调用）、`ForgeConfig.from_env()`（缺 key 时 `SystemExit`） |
| `testforge/variants.py` | 实验条件 B0–B5 的定义 | `VARIANTS` 字典：`rounds` / `gate_enabled` / `feedback_mode` / `continue_on_zero_accept` |
| `testforge/types.py` | 共享数据结构 | `Outcome.killed_mutant`（非 PASS 即杀死）、`VariantResult.ms_all` / `ms_covered` 为派生属性 |
| `testforge/agent/` | 回路编排与 prompt | `orchestrator.py`（`run_target`：基线 → 变异 → 生成 → 门禁 → 联合评估）、`prompts.py`（`=== BLOCK ===` 结构） |
| `testforge/gate/` | 验收判定与原代码执行 | `gate.py`（`evaluate_candidate`）、`runner.py`（`run_tests_once` / `measure_coverage`）、`__init__.py` 里定义 `coverage_pct` |
| `testforge/mutation/` | 变异体生成与杀伤矩阵 | `operators.py`（7 类算子）、`engine.py`（拼接、语法校验、分层采样、编号）、`runner.py`（进程池 + `pytest -x`） |
| `testforge/llm/` | 两个后端 | `client.py`：`OpenAICompatClient`（磁盘缓存/重试/记账）与 `MockLLMClient`（特征化生成） |
| `testforge/analysis/` | 目标函数静态解析 | `inspector.py`：签名、docstring、参数表、行号区间 |
| `testforge/report/` | Markdown 渲染 | `renderer.py`：`render_target_report` / `render_summary` |
| `testforge/utils.py` | 临时工作区、子进程、diff、JSON | `workspace()`（一次性目录，退出即删）、`run_cmd()`（超时返回 -9） |
| `benchmarks/` | 目标函数 + 每模块一份既有测试（B0） | `manifest.json` 是目标清单的唯一来源 |
| `experiments/` | 网格、统计、图、跨网格比较 | `run_experiment.py` / `analyze.py` / `plots.py` / `compare_grids.py` |
| `tests/` | 自身测试 | 9 个文件、49 项，见 `tests/README.md` |
| `results/` | 实验产物 | 只读。`.gitignore` 用白名单只放行 `results/exp_*` 里的 JSON/MD/PNG |

## 关键约定

1. **确定性用 `zlib.crc32`，不用内建 `hash()`**：`orchestrator._stable_hash` 给变异采样种子和候选
   去重哈希用。内建 `hash()` 对 `str` 按进程随机加盐（`PYTHONHASHSEED`），换一次进程就会挑到另一批
   变异体，网格结果不可复现。`llm/client.py` 里 Mock 的测试函数名后缀同样用 crc32。
2. **prompt 磁盘缓存**：`OpenAICompatClient._cache_path` 用 `sha256(model|system|prompt|temperature|max_tokens)`
   作键名写到 `llm_cache/`（或 `TESTFORGE_CACHE_DIR`）。命中即 `cached=True`、零 API 消耗、逐位重放。
   要一次独立采样就把缓存目录指到空目录（已发表的两轮真实网格即如此）。Mock 后端不读写缓存。
3. **逐格落盘、可续跑**：`run_experiment.py` 每跑完一个（目标 × 变体）就把整份 `results.json` 重写一次。
   重启时已完成格打印 `skip ... (cached)`；带 `error` 键的格会被移出 `results.json` 归档到同目录
   `errors.json` 后重跑（`results/exp_api_rq2full/errors.json` 就是这么来的）。
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
   （18 目标 × 2 轮网格），不是测试数。测试数是 49，两处不要互相引用。

## 改动后的验证

| 你动了 | 必须跑 |
|---|---|
| `testforge/**` 任意文件 | `.venv/Scripts/python.exe -m pytest`（49 项通过，约 47 秒） |
| `mutation/operators.py` / `engine.py` | `.venv/Scripts/python.exe -m pytest tests/test_operators.py tests/test_engine.py`；再核对上面那条 197 的计数是否变化 |
| `gate/` | `.venv/Scripts/python.exe -m pytest tests/test_gate.py` |
| `agent/orchestrator.py` / `llm/client.py` | `.venv/Scripts/python.exe -m pytest tests/test_e2e.py tests/test_mock_client.py`，再跑一次离线单格看 MS 是否漂移 |
| `config.py` / `.env` 读取逻辑 | `.venv/Scripts/python.exe -m pytest tests/test_dotenv.py tests/test_config_client.py` |
| `benchmarks/` | `.venv/Scripts/python.exe -m pytest tests/test_inspector.py`（内含“18 个目标”的断言）+ `.venv/Scripts/python.exe -m testforge.cli targets` |
| `cli.py` 参数 | `.venv/Scripts/python.exe -m testforge.cli --help` 与 `run --help`，并至少执行一次离线单格 |
| `experiments/` | 冒烟网格（见 `experiments/README.md`）→ `analyze.py` → `plots.py`，全部指向临时目录 |
| 任一文档 | `cd ../文档标准 && python check_docs.py testforge` |

## 已知坑

- 本地 `.env` 里 `DEEPSEEK_API_KEY=` 是空值。此时 `--mode api` 在建客户端之前就退出，退出码 1，
  原文为：`mode=api requires DEEPSEEK_API_KEY (any non-empty string for unauthenticated internal
  endpoints, see .env.example). Or run with mode=mock for the offline pipeline.`
  不会发出任何网络请求，这是设计行为。
- `TESTFORGE_MODE=api` 对 CLI 不起作用：`cli.py` 的 `--mode` 默认值是字符串 `"mock"`，总会显式传给
  `from_env()`。要切后端只能写 `--mode api`。
- 已发表的三个 90 格网格（`exp_api_full` / `exp_api_replicate` / `exp_mock_full`）用的是
  变异体上限 16、每轮 3 候选、最多 2 轮；今天的默认值是 24 / 4 / 3。直接 `run_experiment.py --mode mock`
  不会复现它们。复核：读对应 `results.json` 里 `mutants_total` 的最大值与 `n_generated` 的最大值。
- `results/exp_api_full/analysis.md` 与 `results/exp_mock_full/analysis.md` 缺当前 `analyze.py` 会写的
  两节（`LLM usage per variant`、`Per-target uplift`）。已有数字未变，只是文件比脚本旧。
- 仓库的 `addopts` 已含 `-q`，再敲 `-q` 就变成 `-qq`，只打印一行圆点、看不到通过数。要数字行就用
  `.venv/Scripts/python.exe -m pytest`。
- `plots.py` 的标题标签取自 `cost.model`。Mock 运行里 `cfg.model` 仍是默认 `deepseek-chat`，所以
  mock 网格的热力图标题会写成 `LLM: deepseek-chat`；跑 mock 网格时显式传 `--label "mock grid"`。
- 两个 `--out` 参数（CLI 与 `run_experiment.py`）都以仓库根为基准拼接，不是当前工作目录。
- `results/` 下只有 `exp_*` 目录的 JSON/MD/PNG 被 git 跟踪；`results/demo/`、`results/demo_owncode/`、
  `results/api_smoke/`、`results/*.log` 是本机历史运行残留，新克隆的仓库里没有。
  `docs/example-report.md` 就是 `results/api_smoke/numeric.integer_sqrt__B3.json` 的渲染结果，
  克隆后无法重跑该核对。
- `docs/report.md` 末尾“36 个自测”与 `docs/interview.md` 的“全管线 36 个自测通过”是旧数字（现为 49）。
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
- 不要为了“看起来有 CI”增加打包/发布流水线；CI 只做安装校验、测试与 CLI 冒烟。
