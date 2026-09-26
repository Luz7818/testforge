# tests/ —— 自身的测试

> 用途：说明这 49 个测试各自盯住哪条行为、哪些断言是故意和具体数字绑在一起的、加测试该照哪个文件写。
> 全部测试离线运行：不发网络请求，也不需要 API key。

运行方式（在仓库根）：

```bash
.venv/Scripts/python.exe -m pytest              # 49 项，本机实测 46.5 秒，末行给出通过数
.venv/Scripts/python.exe -m pytest tests/test_gate.py
```

仓库根的 `conftest.py` 把仓库根插进 `sys.path`，所以 `testforge` 不必安装（本机 `.venv` 里就没有装它）。
`pyproject.toml` 里 `testpaths = ["tests"]`、`addopts = "-q"`：命令行再补一个 `-q` 就成 `-qq`，
只剩一行圆点、看不到通过数。

## 文件清单

| 文件 | 项数 | 盯住什么 |
|---|---|---|
| `test_operators.py` | 9 | 七类算子各一条（AOR/ROR/BCR/CRN/CRS/UOR/RTN 的替换文本），外加三条“不许变异”：docstring、`raise` 的错误消息、类型注解 |
| `test_engine.py` | 6 | 变异体源码仍可 `ast.parse`、与原码不同、`diff` 有内容；id 有序且不重复；上限生效；同种子同选择（确定性）；`splice()` 精确替换；函数名不存在时抛 `ValueError` |
| `test_matrix.py` | 2 | 杀伤矩阵走真实子进程：强测试能杀死 `inc` 的 AOR 变异体，只调用不断言的弱测试一个也杀不死 |
| `test_gate.py` | 5 | 门禁纯判定：全通过 + 有杀伤才验收；flaky、零杀伤分别拒；门禁关闭时单次通过即收；开了 `require_coverage_delta` 且无新覆盖行时拒 |
| `test_mock_client.py` | 3 | Mock 按 `CANDIDATE_COUNT` 给足候选数、两次生成逐字符相同、生成的特征化测试在被捕获的代码上必定通过 |
| `test_inspector.py` | 3 | manifest 里 18 个目标全部能解析出源码与签名；`numeric.clamp` 的签名带注解；`slugify` 的 docstring 能取到 |
| `test_config_client.py` | 6 | `TESTFORGE_EXTRA_BODY` 的空值/对象/非对象/坏 JSON 四种路径；`strip_think()` 去掉推理块与不误伤正文 |
| `test_dotenv.py` | 13 | `.env` 读取：文件值生效、shell 导出优先、空值不能糊弄 `mode=api`、缺文件不算错、注释与坏行跳过、六种取值规范化、`.env` 路径锚在包上而非 cwd、`_load_dotenv()` 必须在模块顶层被调用 |
| `test_e2e.py` | 2 | 整条回路：B3 在 `truncate_with_ellipsis` 上跑通且 MS 不低于 B0、账目至少记一次调用；B3 与 B5 的早退语义（无候选可收时 `rounds_used` 为 1 对 4） |

复核项数：`.venv/Scripts/python.exe -m pytest --collect-only -q`，按文件打印计数，相加为 49。

## 慢在哪

耗时几乎全在 `test_e2e.py`：两条完整回路分别实测 23.3 秒与 20.7 秒，占了全套 46.5 秒里的 44 秒
（复核：`.venv/Scripts/python.exe -m pytest --durations=6`）。其次是起子进程跑真 pytest 的
`test_matrix.py`（1.1 秒与 0.9 秒）和 `test_mock_client.py` 的第三条（0.4 秒）。纯逻辑的
`test_gate.py` 五条不到 0.1 秒（复核：`.venv/Scripts/python.exe -m pytest tests/test_gate.py`）。
改门禁逻辑时先跑快的那个文件。

## 加一个测试

1. 挑同类文件照它的写法加函数：断言具体文本或数值，不用 `assert x is not None` 这种弱断言——
   本项目正是靠“有没有可证伪的断言”判质量，自己的测试不该反过来。
2. 需要真实子进程执行的，参照 `test_matrix.py`：把源码写成字符串常量，用
   `generate_mutants(...)` + `evaluate_mutants(...)`，别去碰 `benchmarks/` 里的文件，那会让
   基准改动连带弄坏测试。
3. 需要构造 prompt 的，参照 `test_mock_client.py` 的 `PROMPT` 常量：`=== BLOCK ===` 分节名必须和
   `testforge/agent/prompts.py` 里写出来的保持一致。
4. 验证：`.venv/Scripts/python.exe -m pytest`，然后确认总数变化写进了仓库根 `AGENTS.md` 的状态表。

## 别动

- `test_dotenv.py` 的 `clean_env` fixture 是自动生效的，它清掉 7 个被管理的环境变量，
  这样开发者本机的 `.env` 不会污染断言。删掉它，这些测试就会随机器环境时好时坏。
- `test_dotenv.py::test_loader_is_called_at_import_time` 用 AST 结构断言而不是重新导入模块，
  文件里的注释解释了原因（重新导入会覆盖被重定向的路径）。不要“顺手改成 reload”。
- `test_inspector.py` 断言目标数是 18：这是加/删基准函数时的登记闸门，改基准就同步改它。
- `test_e2e.py` 第二条把 `max_mutants` 设成 16，因为该设置下 B0 在 `parse_csv_line` 上恰好留一个
  存活变异体，回路才会进第 0 轮（复核：`results/exp_api_full/analysis.md` 里该目标 B0 为 93.8%，
  即 16 个里杀 15 个）。换成别的上限，`rounds_used` 可能变成 0，测试会以一种和改动无关的方式失败。
