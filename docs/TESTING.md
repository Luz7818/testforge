# TestForge 测试规范

> 用途：给写测试和跑门禁的人与 AI。测试数的事实口径在根目录 `AGENTS.md` 的「当前状态」。

## 测试分层

| 层 | 管什么 | 放哪 | 数量级 |
|---|---|---|---|
| 自身单元/集成 | CLI、回路、门禁、预算、diff 解析 | `tests/test_*.py`（13 个文件） | 91 项 |
| 静态检查 | pyflakes | `testforge experiments tests` | 0 项 |
| 冒烟 | 离线单格全链路 | `cli run --mode mock` | 1 格 |
| CI | 4 格测试矩阵 + mutation-loop-smoke + api-smoke（手动） | `.github/workflows/ci.yml` | 5 job |

## 运行命令

```bash
.venv/Scripts/python.exe -m pytest                            # 91 项，约 2.5 分钟
.venv/Scripts/python.exe -m pyflakes testforge experiments tests    # 0 项
.venv/Scripts/python.exe -m testforge.cli run --target numeric.integer_sqrt --variant B3 --mode mock
```

`pyproject.toml` 的 `addopts` 已含 `-q`，再敲 `-q` 变 `-qq` 看不到通过数——要数字行就用上面的
完整命令。

## 用例编写规范

- 测试替身与固定种子：确定性哈希用 `zlib.crc32`（见 `docs/ARCHITECTURE.md` 关键约定 1），
  测试里也不要用内建 `hash()`。
- 新增基准目标必须同步 `tests/test_inspector.py` 的"18 个目标"断言（登记闸门）。
- CI 的 `api-smoke` 是手动 + opt-in（`TESTFORGE_SMOKE_ENABLED=1`），校园网关从公共 runner
  不可达，不配置就自动跳过为绿。

## 改动后的验证

| 你动了 | 必须跑 |
|---|---|
| `testforge/**` 任意文件 | `.venv/Scripts/python.exe -m pytest` |
| `mutation/operators.py` / `engine.py` | `pytest tests/test_operators.py tests/test_engine.py` + 核对 197 候选计数是否变化 |
| `gate/` | `pytest tests/test_gate.py` |
| `agent/orchestrator.py` / `llm/client.py` | `pytest tests/test_e2e.py tests/test_mock_client.py` + 离线单格看 MS 是否漂移 |
| `config.py` / `.env` 读取逻辑 | `pytest tests/test_dotenv.py tests/test_config_client.py tests/test_cost_accounting.py` |
| `benchmarks/` | `pytest tests/test_inspector.py` + `cli targets` |
| `cli.py` 参数 | `--help` 与 `run --help` + 一次离线单格 |
| `experiments/` | 冒烟网格 → `analyze.py` → `plots.py`，全指向临时目录 |
| 任一文档 | `cd ../文档标准 && python check_docs.py testforge` |
