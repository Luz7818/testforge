# benchmarks/ —— 目标函数与基线测试

> 用途：说明这套基准有什么、每个文件管什么、加一个目标函数要走哪几步、哪些东西不能只改一半。

基准是整个实验的输入：被测的 18 个函数、每个模块一份刻意不完整的既有测试（B0），以及一份
把两者对起来的清单。代码本身不含任何测试生成逻辑，改这里不需要改 `testforge/`。

## 目录结构

```text
benchmarks/
├── manifest.json          # 目标清单：id + module + function
├── targets/               # 被测函数，一个模块一个 .py
└── existing_tests/        # B0 既有测试，一个模块一个 test_<模块>.py
```

## 文件清单

| 文件 | 干什么 | 备注 |
|---|---|---|
| `manifest.json` | 唯一的目标登记表，18 条 `{id, module, function}` | `testforge/benchmarks.py` 按约定拼路径：`targets/<module>.py`、`existing_tests/test_<module>.py`，所以文件名不能随便改 |
| `targets/string_utils.py` | `slugify`（转 URL slug）、`mask_email`（日志脱敏）、`truncate_with_ellipsis`（按长度截断加省略号） | 三个函数都带 docstring 写明错误契约 |
| `targets/numeric.py` | `clamp`（夹进闭区间）、`integer_sqrt`（向下取整平方根）、`moving_average`（滑动窗口均值） | — |
| `targets/date_utils.py` | `is_leap_year`、`days_in_month`、`age_in_days`（两个 ISO 日期之间的整天数） | — |
| `targets/containers.py` | `flatten`（任意层嵌套展平）、`chunk`（按大小切片）、`most_frequent`（众数，并列取先出现者） | — |
| `targets/parsers.py` | `parse_csv_line`（含引号与转义）、`parse_version`（点分三段转整数元组）、`parse_kv_pairs` | `parse_csv_line` 是基准里最难杀的目标 |
| `targets/validators.py` | `validate_username`、`validate_port`、`normalize_hex_color`（归一成 `#RRGGBB` 大写） | — |
| `existing_tests/test_*.py` | 各模块的 B0，共 34 个测试函数（复核：`grep -c "^def test_" benchmarks/existing_tests/*.py`） | 故意只覆盖主干路径，边界与错误契约留白 |

一个模块的 B0 会同时用于该模块下的三个目标函数，所以“既有套件”在同一模块的三个目标之间是同一份。

## 每个函数能注入多少变异体

不做采样上限时的全量候选数（复核：`.venv/Scripts/python.exe -c "from testforge.benchmarks import load_targets; from testforge.analysis import inspect_target; from testforge.mutation import generate_mutants; [print(s.target_id, len(generate_mutants(inspect_target(s).module_source, s.function_name, max_mutants=10**6))) for s in load_targets()]"`）：

| 模块 | 函数与候选数 | 小计 |
|---|---|---|
| `string_utils` | slugify 8 · mask_email 21 · truncate_with_ellipsis 12 | 41 |
| `numeric` | clamp 6 · integer_sqrt 21 · moving_average 11 | 38 |
| `date_utils` | is_leap_year 17 · days_in_month 9 · age_in_days 3 | 29 |
| `containers` | flatten 6 · chunk 5 · most_frequent 7 | 18 |
| `parsers` | parse_csv_line 24 · parse_version 12 · parse_kv_pairs 7 | 43 |
| `validators` | validate_username 9 · validate_port 5 · normalize_hex_color 14 | 28 |
| 合计 | — | 197 |

上限会截掉一部分：默认 `max_mutants=24` 时全量仍是 197（只有 `parse_csv_line` 正好卡在上限）；
已发表的三个 90 格网格用的是 16/目标，截完是 178 个。

## 加一个目标函数

1. 在 `targets/` 对应模块里加函数，docstring 写清边界与抛什么异常——prompt 会原样带给模型。
2. 若新建模块：在 `existing_tests/` 加 `test_<模块名>.py`，模块内每个函数都要有测试。
   这份文件必须在原代码上全通过，否则 `run` 会以
   `[<id>] existing tests fail on the original code (fail)` 中止。
3. 在 `manifest.json` 的 `targets` 数组里追加一条。
4. 改 `tests/test_inspector.py` 里“18 个目标”的断言，那是有意的登记闸门。
5. 验证：

```bash
.venv/Scripts/python.exe -m pytest tests/test_inspector.py
.venv/Scripts/python.exe -m testforge.cli targets
.venv/Scripts/python.exe -m testforge.cli run --target <新 id> --variant B3 --mode mock --out ../tf_check
```

## 和谁打交道

- **上游**：无（这里是原始输入）。
- **下游**：`testforge/agent/orchestrator.py` 读目标与 B0；`experiments/run_experiment.py` 用
  `load_targets()` 展开网格；`testforge/cli.py targets` 打印清单。
- **改这里之后要跑**：`pytest tests/test_inspector.py` + 上面的单格命令；如果动了函数语义，
  `results/` 下已发表网格的绝对分数即不再可比，不要拿它们和新数字混在一张表里。

## 别动

- 不要让 `targets/*.py` 与 `existing_tests/test_*.py` 的模块名不一致：路径是按
  `test_{module}.py` 拼出来的，拼错时 B0 会读成 `# no existing tests`，基线悄悄变成空集。
- 不要往函数里加随机、时钟、网络或文件 IO：门禁要在原代码上连跑 5 次，非确定的函数会被判成 flaky。
- 不要为了“让分数好看”去补 B0 的缺口。B0 留白正是这套基准的意义，改了它历史网格全部作废。
- `results/` 里已发表网格引用的变异体编号来自当前的算子集，改 `benchmarks/targets/` 的函数体
  会让这些编号重排。
