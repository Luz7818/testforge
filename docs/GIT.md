# TestForge Git 规范

> 用途：给提交本仓代码的人。分支、CI、入库边界都在这里。

## 分支与提交策略

- 单 `main` 分支，推 `main` 触发 CI（5 job：4 格测试矩阵 + mutation-loop-smoke + api-smoke）。
- **一批一提交**；提交前门禁：pytest 全绿 + pyflakes 0 项 + `--preset published` Mock 网格
  指纹不变（整理/精简类改动，见 README「贡献与许可」）。
- 已发表数字相关改动的铁律：**不要改 `results/` 已提交产物来"让数字对得上"**——重跑实验到
  新目录，再改文档引用。

## 必须入库 / 禁止上传

| 判定 | 规则 |
|---|---|
| 必须入库 | `testforge/`、`benchmarks/`、`experiments/`、`tests/`、`results/exp_*/`（白名单：JSON/MD/PNG）与 `results/README.md`、`llm_cache/`（prompt 缓存，命中即免费重放）、`action.yml`、文档 |
| 禁止上传 | `.env`（含校园网关密钥；模板 `.env.example`）、`results/` 白名单外的本机残留（`demo/`、`*.log` 等）、`.ruff_cache/`、`__pycache__/` |
| 缓存边界 | `llm_cache/` 文件名 = prompt 指纹，不要手改；独立采样走子目录，不混入已发表网格的缓存 |

## CI

- `.github/workflows/ci.yml`：4 格测试矩阵（ubuntu 3.10/3.11/3.12 + windows 3.12）+
  `mutation-loop-smoke`（pyflakes + 一格 Mock 全链路 + 结果断言）+ `api-smoke`（手动 opt-in）。
- `.github/workflows/quality-gate.yml`：本仓自身 PR 由 action 以 mock 模式门禁（确定性零成本）。
- 不要往 CI 里加打包/发布流水线。

## commit message

- 风格沿用既有历史：`<type>(<scope>): 中文一句话` 或 `<type>: 中文一句话`
  （复核：`git log --oneline -10`）。
- tag：v0.1.0–v0.6.0 已有 tag；v0.1–v0.3 的 8B 网格归档在 tag v0.3.0。
