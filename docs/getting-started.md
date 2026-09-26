# TestForge 上手手册

> 用途：给要真的把它用起来或改它的人。每一步给命令、给本机真实输出、给出错时怎么办。
> 阅读顺序：从第 1 节往下做，不需要跳读。术语第一次出现都有一句解释，第 9 节汇总成小词典。
> 本文所有命令都在仓库根目录执行；Windows 用 `.venv/Scripts/python.exe`，Linux/macOS 换成 `.venv/bin/python`。

## 1. 你需要准备什么

| 项目 | 要求 | 怎么确认 |
|---|---|---|
| 操作系统 | Windows / Linux 均可（CI 两种都跑） | — |
| 运行时 | Python 3.10 以上；仓库自带 `.venv`，本机为 3.12.0 | `.venv/Scripts/python.exe --version` |
| 第三方依赖 | `pytest`、`coverage`、`openai`、`matplotlib` 四项（清单在 `pyproject.toml`） | `.venv/Scripts/python.exe -m pip list` |
| 网络 | 离线 Mock 全流程用不到。`--mode api` 才需要能访问端点 | — |
| 密钥 | 只有 `--mode api` 需要，见第 4 节；本机 `.env` 里那一项是空的也能跑 Mock | — |
| 安装本包 | 不需要。命令都从仓库根以 `.venv/Scripts/python.exe -m testforge.cli ...` 或 `... experiments/<脚本>.py` 运行 | `.venv/Scripts/python.exe -m pip list` 查不到 `testforge` 条目 |

依赖没装齐时的最小需求分两档：只跑 `run`/`report` 需要 `pytest` 与 `coverage`；`openai` 只在
`--mode api` 时才被导入（`testforge/llm/client.py` 里是懒加载）；`matplotlib` 只被
`experiments/plots.py` 用到。

## 2. 认一下目标清单

```bash
.venv/Scripts/python.exe -m testforge.cli targets
```

输出 18 行，每行一个目标 id 和它所在的模块（数一下就是 18 行）。前 5 行：

```text
string_utils.slugify                     module=string_utils
string_utils.mask_email                  module=string_utils
string_utils.truncate_with_ellipsis      module=string_utils
numeric.clamp                            module=numeric
numeric.integer_sqrt                     module=numeric
```

每个目标 = 一个模块里的一个函数，另配一份该模块的既有测试作为基线 B0。B0 是故意留缺口的，
缺口就是后面变异测试要暴露的东西。

## 3. 离线 Mock 全流程（分析 → 变异 → 生成 → 门禁 → 反馈 → 报告）

```bash
.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock
```

本机真实输出（49 秒，退出码 0）：

```text
numeric.integer_sqrt                     B3  MS(all)= 76.2%  MS(cov)= 76.2%  gen=8   acc=2        49s
```

四个字段：`MS(all)` 是最终套件的变异分数（被杀死的变异体 / 全部变异体），`MS(cov)` 只把被执行到的
变异体算进分母，`gen` 是生成的候选数，`acc` 是被验收进套件的候选数。

这一条命令背后按顺序发生了六件事，逐段对应代码：

| 步骤 | 做什么 | 代码位置 |
|---|---|---|
| 1 基线 | 把 B0 在原代码上跑一遍，跑不过就中止 | `testforge/agent/orchestrator.py` 的 `run_target` 第 1 段 |
| 2 变异 | 给目标函数注入变异体，先找出 B0 已经杀死的 | `testforge/mutation/engine.py` + `runner.py` |
| 3 生成 | 每轮向后端要 K 个候选测试文件（Mock 在本地合成） | `testforge/agent/prompts.py` + `testforge/llm/client.py` |
| 4 门禁 | 候选要在原代码上连过 5 次，且至少杀死一个存活变异体 | `testforge/gate/gate.py` + `runner.py` |
| 5 反馈 | 存活变异体以 diff 形式回填进下一轮 prompt | `orchestrator.py` 的 `build_feedback_prompt` 调用 |
| 6 联合评估 | 全套件重跑所有变异体，定最终分数与覆盖率 | `orchestrator.py` 第 4 段 |

产物写在 `--out` 指定的目录（默认 `results/runs/`）：一格一个 JSON，外加一份 `summary__B3.md` 表格。
把 JSON 再渲染成单目标 Markdown 报告（含逐变异体的杀伤归因表）：

```bash
.venv/Scripts/python.exe -m testforge.cli report --results results/runs/numeric.integer_sqrt__B3.json --out my_report.md
```

输出把 `--out` 路径原样回显：

```text
report written to my_report.md
```

Mock 后端是种子化的，不掺随机：同一条 `run` 命令跑两遍，两份 JSON 里除 `wall_sec` 之外逐字段相同
（复核：跑两遍到两个 `--out` 目录，再逐字段比较）。想只看门禁、不要反馈回路，把变体换成 `B2`；
想只看既有套件的成绩，换成 `B0`（`B0` 一次 LLM 调用都不发）。

## 4. 接真实 LLM 端点

只支持 OpenAI 兼容的 `/chat/completions` 服务：DeepSeek 或自建的 vLLM、Ollama 等。要配的
环境变量只有名字与作用（值请自己填，注释必须独占一行，行内 `#` 会被当成值的一部分）：

| 变量 | 作用 | 不填会怎样 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 建连用的凭据字符串；不鉴权的内网端点填任意非空串 | `--mode api` 立刻以退出码 1 结束，不发请求 |
| `TESTFORGE_MODEL` | 请求体里的模型名 | 用 `testforge/config.py` 的默认值 `deepseek-chat` |
| `TESTFORGE_API_BASE` | 端点 base URL | 默认 `https://api.deepseek.com` |
| `TESTFORGE_EXTRA_BODY` | 一段 JSON，合并进每次请求体（服务端私有开关） | 不附加任何参数 |
| `TESTFORGE_MAX_TOKENS` | 单次响应长度上限；一次响应要装下 K 个候选 | 默认 2048，候选数一多尾部候选会被截断 |
| `TESTFORGE_CACHE_DIR` | prompt 缓存目录 | 默认写到仓库根 `llm_cache/` |
| `TESTFORGE_MODE` | 只在代码里调 `ForgeConfig.from_env()` 且不传 `mode` 时才起作用 | CLI 总会把 `--mode` 显式传进去，所以写了也没用 |

仓库根的 `.env` 在导入 `testforge.config` 时自动读取，优先级是 shell 导出 > `.env` > 代码默认值，
所以导出过的变量不会被文件覆盖。复制 `.env.example` 为 `.env` 再填即可。

跑一条真实的候选生成（会向端点发请求，本文不代跑）：

```bash
.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode api
```

同一条 prompt 第二次跑会命中 `llm_cache/`：账目里 `cached` 为真、零 API 消耗、逐字节重放。
要一份独立的新采样，就把 `TESTFORGE_CACHE_DIR` 指到一个空目录——已发表的两轮真实网格就是这么得到的。

## 5. 跑一份自己的代码

三个参数：模块文件、函数名、（可选）该模块已有的测试文件。

```bash
.venv/Scripts/python.exe -m testforge.cli run --module benchmarks/targets/containers.py --function chunk --tests benchmarks/existing_tests/test_containers.py --variant B3 --mode mock
```

本机真实输出（16 秒，退出码 0）：

```text
containers.chunk                         B3  MS(all)=100.0%  MS(cov)=100.0%  gen=4   acc=1        16s
```

要求与限制：

- 模块是单个 `.py` 文件，文件名必须是合法的 Python 标识符（生成的测试会按这个文件名 import）。
- 函数是确定性纯函数：不读网络、时钟、随机数，也不写文件，否则门禁的重复运行检查会把它判成 flaky。
- 不传 `--tests` 时 B0 视为空套件，此时“既有测试已杀死的变异体”为零，全部变异体都算存活。
- `--tests` 指向的文件必须在原代码上全通过；有一条不过就中止（见第 7 节）。

目标函数简单到 B0 已能杀光全部变异体时，回路一步都不会走，也就不会发任何 LLM 调用。拿这两份两三个
行的文件就能重现。把它们存到仓库之外的临时目录（下文写成 `../tf_own/`，换成你机器上的实际路径即可，
`--out` 同理）：

```python
def double(x: int) -> int:
    """Return twice x."""
    return x * 2
```

```python
from myutils import double


def test_double():
    assert double(2) == 4
```

```bash
.venv/Scripts/python.exe -m testforge.cli run --module ../tf_own/myutils.py --function double --tests ../tf_own/test_myutils.py --variant B2 --mode mock --out ../tf_own_out
```

```text
myutils.double                           B2  MS(all)=100.0%  MS(cov)=100.0%  gen=0   acc=0         4s
```

这是正常结果，不是没跑起来。核对方式：产物 JSON 里 `mutants_total` 为 3、`cost.calls` 为 0，
`mutant_summary` 三行全是 `killed_by_b0: true`——三个变异体（`RTN`、`AOR`、`CRN`）B0 已经全杀了。

## 6. 跑实验网格与出图

网格 = （目标 × 变体）的笛卡儿积，一格一次完整回路。先用两个目标、两个变体做一次冒烟，
产物写到仓库之外，免得和 `results/` 下已发表的网格混在一起：

```bash
.venv/Scripts/python.exe experiments/run_experiment.py --mode mock --targets numeric.clamp,numeric.moving_average --variants B0,B1 --out ../tf_smoke
```

本机真实输出（4 格约 25 秒，退出码 0；`done ->` 那行会把传入的 `--out` 原样拼在仓库根后面）：

```text
[1/4] numeric.clamp                            B0  ok       4s
[2/4] numeric.clamp                            B1  ok       4s
[3/4] numeric.moving_average                   B0  ok       6s
[4/4] numeric.moving_average                   B1  ok      11s
done -> D:\东南大学\项目\Project\testforge\..\tf_smoke
```

同一个 `--out` 再跑一次，已完成的格直接跳过——这就是中断后续跑的方式：

```text
[1/4] skip numeric.clamp B0 (cached)
[2/4] skip numeric.clamp B1 (cached)
[3/4] skip numeric.moving_average B0 (cached)
[4/4] skip numeric.moving_average B1 (cached)
done -> D:\东南大学\项目\Project\testforge\..\tf_smoke
```

出统计与图（`analyze.py` 会覆写 `--exp` 目录里的 `analysis.md` / `analysis.json`，所以别把它指向
`results/` 下的已发表网格）：

```bash
.venv/Scripts/python.exe experiments/analyze.py --exp ../tf_smoke
.venv/Scripts/python.exe experiments/plots.py --exp ../tf_smoke --label "smoke"
```

```text
analysis -> ..\tf_smoke\analysis.md
plots -> ..\tf_smoke\plots
```

图会少几张是正常的：`tokens_by_variant.png`（没有 token）、`uplift_vs_cost.png`（缺 B0 或 B3）、
`gate_rejections.png`（一次拒绝都没有）在条件不满足时直接跳过。跑完删掉临时目录即可。

常用参数：

| 参数 | 作用 | 默认值 |
|---|---|---|
| `--targets` | `all` 或逗号分隔的目标 id | `all` |
| `--variants` | 逗号分隔的变体名 | `B0,B1,B2,B3,B4` |
| `--max-mutants` | 每目标变异体上限（超过则按算子分层采样） | 24 |
| `--candidates` | 每轮向模型要几个候选 | 4 |
| `--rounds` | B3/B4/B5 的最大反馈轮数 | 3 |
| `--flaky-runs` | 门禁在原代码上重复几次 | 5 |
| `--out` | 输出目录，相对仓库根解析 | `results/exp_<模式>_<时间戳>` |

想复现已发表的那三张 90 格网格，参数得写全：它们用的是 `--max-mutants 16 --candidates 3 --rounds 2`，
与今天的默认值不同。

## 7. 想改它

### 7.1 加一个目标函数

1. 往 `benchmarks/targets/` 里对应的模块加函数（或新建模块），带 docstring 写清错误契约——
   prompt 会把它原样发给模型。
2. 若新建模块：在 `benchmarks/existing_tests/` 加一份 `test_<模块名>.py`，模块内三个函数都要有测试，
   但可以故意留边界缺口。
3. 在 `benchmarks/manifest.json` 的 `targets` 数组里加一条 `{id, module, function}`。
4. `tests/test_inspector.py` 里断言目标是 18 个，需要同步改这个数。
5. 验证：

```bash
.venv/Scripts/python.exe -m pytest tests/test_inspector.py
.venv/Scripts/python.exe -m testforge.cli targets
.venv/Scripts/python.exe -m testforge.cli run --target <新 id> --variant B3 --mode mock --out ../tf_check
```

第二行要列出你的 id，第三行给出一个非空的 `MS(all)`。若 `RuntimeError: no mutants could be generated`
就说明这个函数里没有可注入语义变化的表达式，换函数或接受它不适用。

### 7.2 加一个变异算子

1. 在 `testforge/mutation/operators.py` 的 `find_mutation_candidates()` 里加一个 `elif` 分支，返回
   `MutationCandidate(node, replacement, operator, description)`。`node` 必须是带位置的 AST 节点，
   `replacement` 是同一段位置的源码文本（算子类要先 `copy.deepcopy` 换掉 op 再 `ast.unparse`）。
2. 决定要不要把它挡在某些节点前：注解、docstring、`raise` 里的错误消息字符串已在
   `_collect_skip_ids()` / `_is_docstring_constant()` 里被排除，理由是它们产生近等价变异体，只会稀释分数。
3. 在 `testforge/types.py` 的 `Mutant.operator` 注释与 `testforge/mutation/operators.py` 的模块
   docstring 里补上新算子名。
4. 加单测（照 `tests/test_operators.py` 的写法：给一小段源码，断言算子名与 `replacement` 文本），
   再加一条“不该被变异”的用例。
5. 验证：

```bash
.venv/Scripts/python.exe -m pytest tests/test_operators.py tests/test_engine.py
```

注意：新算子会改变每个目标的变异体全集，`results/` 下已发表网格的绝对分数因此不再可比。
仓库根的 `AGENTS.md` 里那条“197 个候选”的计数命令也会变，改完顺手更新它。

## 8. 常见故障

| 现象 / 报错原文 | 原因 | 处理 |
|---|---|---|
| `mode=api requires DEEPSEEK_API_KEY (any non-empty string for unauthenticated internal endpoints, see .env.example). Or run with mode=mock for the offline pipeline.`（退出码 1） | `--mode api` 但 key 缺失或是空串，代码在建连之前就拦下 | 填 `.env` 或导出变量；只想看流程就用 `--mode mock` |
| `unknown variant 'B9'; choose from ['B0', 'B1', 'B2', 'B3', 'B4', 'B5']` | 变体名写错 | 变体只有这六个，含义见 `testforge/variants.py` |
| ``unknown target 'nope.nope'; run `python -m testforge.cli targets``` | `--target` 的 id 不在 `benchmarks/manifest.json` 里 | 先跑 `targets` 抄 id |
| `provide either --target <benchmark-id> or --module <path> --function <name>` | `run` 既没给 `--target`，也没给齐 `--module` + `--function` | 二选一补全 |
| `module file not found: ...` / `existing test file not found: ...` | 路径相对当前工作目录解析后不存在 | 用相对仓库根的路径或绝对路径 |
| `ValueError: function 'nope' not found in <模块绝对路径>`（未捕获，带 traceback，退出码 1） | `--function` 的名字在该模块里不存在（或是个类里的方法/只是个变量） | 填模块顶层函数名 |
| `RuntimeError: [badmod.f] existing tests fail on the original code (Outcome.FAIL)`（未捕获，带 traceback，退出码 1） | 你改过 B0 或目标函数，二者已经不一致；基线跑不过就没法归因 | 把 B0 修到在原代码上全通过；或换 `--tests` 指向的文件。括号里是被格式化出来的 `Outcome` 枚举 |
| `RuntimeError: [empt.noop] no mutants could be generated` | 函数体里没有可替换的算子、常量或返回值（例如只有 `print`） | 换目标函数，或接受该函数不适用变异测试 |
| `unknown targets: ['a.b']`（`run_experiment.py`） | `--targets` 里有 manifest 之外的 id | 照 `cli targets` 的输出改 |
| `unknown variant 'B7'`（`run_experiment.py`） | `--variants` 里有未定义的变体 | 变体定义在 `testforge/variants.py` |
| 跑完 `gen=0`、`acc=0`，`MS(all)` 与既有套件一致 | 用的是 `--variant B0`：它只给既有套件打分，一次 LLM 调用都不发 | 换 `B1`/`B2`/`B3` |
| 真实端点跑完 `acc=0` 且 `rejection_reasons` 里全是 `falsifiable` | 模型给的候选都能跑、但杀不死任何存活变异体 | 正常结论（说明没有可证明的增量）。要提升就换更强模型或加大 `--rounds` |
| `.venv/Scripts/python.exe -m pytest -q` 只输出一行圆点，看不到通过数 | `pyproject.toml` 的 `addopts` 已经带 `-q`，再 `-q` 就成了 `-qq` | 用 `.venv/Scripts/python.exe -m pytest`，末行是 `49 passed in ...` |
| 报错信息里的中文路径显示成一串方块与乱码（ASCII 段正常） | 项目路径含中文，控制台按 GBK 解码 Python 写出的 UTF-8 字节 | 先 `set PYTHONIOENCODING=utf-8` 再跑（实测有效）。子进程里的测试执行不受影响：`testforge/utils.py` 已强制 UTF-8 |
| `ModuleNotFoundError: No module named 'testforge'` | 不在仓库根执行，或用了没装依赖的外部解释器 | `cd` 到仓库根，用 `.venv/Scripts/python.exe` |

## 9. 术语小词典

| 词 | 在本项目里指什么 |
|---|---|
| 变异体（mutant） | 把目标函数做一处小改动（`+`→`-`、`<`→`<=`、常量 `0`→`1`、`return x`→`return None` 等）得到的那份代码，代表一个种子 bug |
| 变异分数（MS） | 被杀死的变异体占比。`MS(all)` 分母是全部变异体，`MS(cov)` 只算被执行到的那批 |
| 杀死 | 拿变异后的代码跑测试，套件没有全通过（断言失败、报错或超时）就算杀死。超时也计杀死，因为行为确实变了 |
| 存活 | 变异体在被改过的代码上仍让全套件通过——说明没有任何测试约束这段行为，它就是要补的缺口 |
| 门禁 | 验收候选的判据：在原代码上连过 5 次（防 flaky）+ 至少杀死一个存活变异体（可证伪）。覆盖率默认只报告不强制 |
| 预言机（oracle） | 测试里“什么算对”的那部分。弱预言机如 `assert result is not None`，强预言机断言精确值与异常类型 |
| few-shot | 本仓库没有示例库。prompt 里充当上下文示例的是既有测试文件（`=== EXISTING_TESTS ===`）与存活变异体清单（`=== SURVIVING_MUTANTS ===`） |
| 早退 | B3 的一条工程规则：某轮一个候选都没验收，就停止迭代、不再问模型。B5 的唯一差别是取消它 |
| B0–B5 | 六个实验条件：既有套件 / 单次生成无门禁 / 单次+门禁 / 完整回路 / 覆盖缺口反馈消融 / 不早退、把 4 轮预算走完的回路 |
| 杀伤矩阵 | 每个（变异体 × 测试套件）对跑一次的表，`MS`、门禁与反馈都从它取数 |
| prompt 缓存 | 以模型+prompt+温度+长度上限的 sha256 为文件名的响应缓存，在 `llm_cache/` |

## 10. 改完之后跑什么

```bash
.venv/Scripts/python.exe -m pytest
```

退出码 0、末行 `49 passed in ...`（本机两次实测 46.5 秒与 45.7 秒；同时跑别的任务会拉长）。再跑一次第 3 节的离线单格，看 `MS(all)`、
`gen`、`acc` 有没有意外漂移。每条门禁命令管什么的说明在仓库根的 [AGENTS.md](../AGENTS.md)。
