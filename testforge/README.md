# testforge/ —— 包本体

> 用途：说明这个包里每个模块管哪一段、每个文件里有什么可调用的东西、改动后要跑什么。
> 一句话概括：`analysis` 读函数 → `mutation` 造 bug → `llm` 出候选 → `gate` 判收 → `agent` 串成回路
> → `report` 写 Markdown → `cli` 把人接进来。

本包不依赖任何服务，也不写数据库：所有中间产物是临时目录里的一次性文件，只有 `--out` 指定的
JSON/Markdown 和 `llm_cache/` 里的 prompt 缓存会留在磁盘上。

## 顶层文件

| 文件 | 干什么 | 备注 |
|---|---|---|
| `__init__.py` | 包说明与 `__version__ = "0.1.0"` | CLI 的 `--version` 读它 |
| `cli.py` | 三个子命令：`targets` / `run` / `report` | `run` 的顺序是读配置 → 取变体 → 解析目标 → 跑 → 落盘；`--variant` 默认 `B3`，`--mode` 默认 `mock`，`--out` 默认 `results/runs`（相对仓库根解析） |
| `config.py` | 全部旋钮 + 零依赖 `.env` 读取 | `_load_dotenv()` 在模块顶层被调用；`from_env()` 在 `mode=api` 且 key 为空时 `SystemExit`；`workers` 默认 `max(2, min(8, cpus-2))`；两个 `price_*` 是占位单价 |
| `types.py` | 共享数据结构 | `Outcome`（pass/fail/error/timeout，非 pass 即杀死）、`TargetSpec`、`TargetInfo`、`Mutant`、`Candidate`、`GateVerdict`、`VariantSpec`、`VariantResult`（`ms_all`/`ms_covered` 是派生属性）、`CostLedger` |
| `variants.py` | 实验条件 B0–B5 的唯一定义 | `VARIANTS` + `get_variant()`；`--variant` 与 `run_experiment.py --variants` 都读这张表 |
| `benchmarks.py` | 读 `benchmarks/manifest.json` 拼出 `TargetSpec` | `load_targets()` / `get_target()` / `result_to_dict()`；模块路径与 B0 路径按约定拼，不在 manifest 里写 |
| `utils.py` | 一次性工作区、子进程、diff、JSON | `workspace()` 建临时目录并在退出时删除；`run_cmd()` 强制 UTF-8、超时返回 -9；`mini_diff()` 给 prompt 与日志用 |

## agent/ —— 回路编排

| 文件 | 干什么 | 备注 |
|---|---|---|
| `orchestrator.py` | `ForgeAgent.run_target()`：基线 → 变异 → 生成/门禁/反馈循环 → 最终联合评估 | 四段结构对应 `docs/getting-started.md` 第 3 节的表 |
| `orchestrator.py` 内 `_stable_hash` / `_norm_hash` | 变异采样种子、候选去重 | 用 `zlib.crc32` 而非内建 `hash()`，理由见仓库根 `AGENTS.md` |
| `orchestrator.py` 内 `_maybe_repair` | 语法坏掉的候选给一次修复机会 | 只在 `mode=api` 生效，Mock 产出的文件必定可解析 |
| `prompts.py` | `build_initial_prompt` / `build_feedback_prompt` / `build_repair_prompt` | 全文用 `=== BLOCK ===` 分节，真实模型与 Mock 共用同一套解析 |
| `__init__.py` | 导出 `ForgeAgent` | — |

反馈轮里最多贴 8 条存活变异体（`max_feedback_mutants`），每条写成 `[M008] line 17 (CRN): \`i + 1\` -> \`i + 2\``。
覆盖率消融分支（B4）改贴未覆盖行号，最多 30 行。

## gate/ —— 验收判定与执行

| 文件 | 干什么 | 备注 |
|---|---|---|
| `gate.py` | `GatePolicy` 与 `evaluate_candidate()`：算出 `GateVerdict` | 开启门禁时两项判据：`runs_on_original`（N 次全过）、`falsifiable`（至少杀一个存活变异体）；`coverage_delta` 仅在 `require_coverage_delta=True` 时才当判据 |
| `runner.py` | `run_tests_once()` 跑候选、`measure_coverage()` 量行覆盖 | 后者用 `coverage run --include=<模块>.py` + `coverage json`，返回（结果, 已执行行, 可执行行）；把覆盖数据转成 JSON 那一步固定 60 秒上限（`_COVERAGE_TIMEOUT`） |
| `__init__.py` | 再导出上面这些，并且在这里定义了 `coverage_pct()` | 别从 `gate.gate` 导 `coverage_pct`，它不在那儿 |
| `__init__.py` 的 `coverage_pct()` | 分母只算可执行行 | 注释与 docstring 不计入，所以覆盖率不会被空行抬高 |

`gate_enabled=False`（B1）时只跑一次、只看这一次通过与否——就是“模型给什么收什么”的开发方式。

## mutation/ —— 变异体生成与杀伤矩阵

| 文件 | 干什么 | 备注 |
|---|---|---|
| `operators.py` | 7 类算子的候选发现：AOR、ROR、BCR、CRN、CRS、UOR、RTN | `_AOR` / `_ROR` 是替换表，每个位置只取一个替代；`_collect_skip_ids()` 排除注解与 `raise` 里的错误消息，`_is_docstring_constant()` 排除 docstring |
| `engine.py` | `generate_mutants()`：源码拼接 → `ast.parse` 校验 → 去重 → 分层采样 → 按行号排序编号 | `splice()` 按 UTF-8 字节偏移换算字符位置，非 ASCII 源码也不会错位；超过 `max_mutants` 才触发 `_stratified_sample()` |
| `runner.py` | `evaluate_mutants()`：一个（变异体 × 套件）对一个子进程，进程池并行 | `_PYTEST_ARGS` 带 `-x`，首个失败即结束；`classify_rc()` 把退出码 0 和 5 都记 PASS、-9 记 TIMEOUT |
| `__init__.py` | 导出 `generate_mutants` / `evaluate_mutants` | — |

变异体 id 形如 `M001`，在采样与排序之后重新编号：换上限或换目标 id（改变种子）都会让编号重排。

## llm/ —— 两个可换后端

| 文件 | 干什么 | 备注 |
|---|---|---|
| `client.py` | `SYSTEM_PROMPT`、`LLMResponse`、`strip_think()`、`OpenAICompatClient`、`MockLLMClient`、`make_client()` | 一个文件里放两个后端与响应切分逻辑，`make_client(cfg, root)` 按 `cfg.mode` 选 |
| `client.py` 的 `LLMResponse.split_candidates()` | 按 `# ==== CANDIDATE k ====` 标记切多个候选 | 没有标记时，整段文本只要以 `#` / `import` / `from` / 引号开头就当成一个候选 |
| `client.py` 的 `OpenAICompatClient` | 调用、重试（指数退避，`llm_retries` 次）、按 sha256 指纹读写 `llm_cache/`、算 token 与成本 | `openai` 是懒加载：`--mode mock` 不需要装它 |
| `client.py` 的 `MockLLMClient` | 离线确定性生成器：执行目标函数、把观测到的返回值/异常冻成断言 | 每个候选 3 组输入；输入取自 `_VALUES`，按参数注解或参数名猜类型；轮次 >0 时只取每个取值池偏边界的前 1/3；测试名后缀是 `crc32` 取模（返回值用例 `% 100000`，`pytest.raises` 用例 `% 10000`） |
| `__init__.py` | 导出 `LLMResponse` / `make_client` | — |

Mock 只记录 token 为 0，`CostLedger` 里的 `model` 仍是配置中的模型名（默认 `deepseek-chat`），
这会让 `plots.py` 的标题把它当成真实模型，见仓库根 `AGENTS.md` 的“已知坑”。

## analysis/ —— 目标函数的静态解析

| 文件 | 干什么 | 备注 |
|---|---|---|
| `inspector.py` | `inspect_target(spec)` → `TargetInfo`：签名行、docstring、参数表、函数源码、起止行号 | `_params_of()` 覆盖位置参数、仅关键字、`*args`、`**kwargs`；找不到函数抛 `ValueError` |
| `__init__.py` | 导出 `inspect_target` | — |

起止行号后面被两处用到：把覆盖率限定在该函数内、把变异体归属限定在该函数子树。

## report/ —— Markdown 渲染

| 文件 | 干什么 | 备注 |
|---|---|---|
| `renderer.py` | `render_target_report()` 单目标报告（Headline / Gate rejections / Mutants / Accepted tests）；`render_summary()` 多目标一行一格的表 | 纯字符串拼接，无第三方模板库；`docs/example-report.md` 就是它的产物 |
| `__init__.py` | 导出上面两个函数 | `cli report` 与 `run_experiment.py` 都在用 |

## 和谁打交道

- **上游**：`benchmarks/manifest.json`（目标清单）、`benchmarks/targets/*.py`（被测源码）、
  `benchmarks/existing_tests/*.py`（B0）、`.env`（端点配置）。
- **下游**：`--out` 目录里的 JSON 与 `summary__<变体>.md`、`llm_cache/` 里的 prompt 缓存、
  临时目录（跑完即删）。
- **改这里之后要跑**：`.venv/Scripts/python.exe -m pytest`，再跑一遍
  `docs/getting-started.md` 第 3 节的离线单格，比较 `MS(all)` / `gen` / `acc` 是否漂移。

## 别动

- 不要把 `--out` 的默认值改成 `results/` 之外的路径：`.gitignore` 里对 `results/exp_*` 有白名单，
  改法会让已发表网格的产物落进版本库或被忽略。
- 不要放宽 `Outcome.killed_mutant`（非 pass 即杀死）或 `classify_rc` 里 rc=5 记 PASS 的口径，
  杀伤矩阵的所有分数都建立在这两条上。
- 不要在 prompt 里塞时间戳、随机数或绝对路径：`llm_cache/` 的文件名是 prompt 的 sha256，
  任何不稳定字节都会让缓存失效、让“重放逐位一致”不再成立。
- `SYSTEM_PROMPT` 与 `=== BLOCK ===` 分节名是 Mock 的解析依据（`_block("MODULE_SOURCE")` 等），
  改名字要同步改 `MockLLMClient`。
