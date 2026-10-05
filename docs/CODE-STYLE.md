# TestForge 代码风格

> 用途：给改本仓代码的人与 AI。约定来自既有实践；静态检查是 pyflakes（无 ruff/black 配置）。

## 代码风格

- Python ≥3.10，stdlib 优先；运行时依赖只有 `pytest`/`coverage`/`openai`，
  `matplotlib` 在可选组 `plots`（出图才装）。
- 零依赖实现优先：Wilcoxon/bootstrap 统计、`.env` 读取、diff 解析都是手写 stdlib 实现，
  不要为此引入 numpy/scipy/python-dotenv。

## 命名与结构约定

- 实验变体 B0–B5 定义单源在 `variants.py` 的 `VARIANTS`；网格参数单源在 `presets.py`。
- 结果目录 `results/exp_<描述>[_rep]/`（独立采样带 `_rep` 后缀）；缓存子目录按网格命名。
- 确定性哈希统一 `zlib.crc32`（`_stable_hash`、Mock 测试名后缀）——禁止内建 `hash()`。

## 错误处理与已知陷阱

- 缺配置 fail-fast：`ForgeConfig.from_env()` 缺 key 时 `SystemExit`，不带空凭据发请求。
- 子进程超时返回 -9（`run_cmd()`）；TIMEOUT 计为杀死变异体。
- API 层错误要响亮：空响应 + `finish_reason=length` 是可重试错误，不许静默产出零候选格。
- 验收门禁看 `falsifiable`（至少杀一个存活变异体），不要放宽成"覆盖率有提升就行"，
  也不要把 `coverage_delta` 设为默认强制（与 TestGen-LLM 式验收的差别，`docs/report.md` §4.3）。
