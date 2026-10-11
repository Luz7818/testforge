# TODO —— 开发计划与当前进度

> 用途：给开发者与 AI。当前在做哪个任务、每个任务按什么标准验收、接下来做什么。
> 完成一项就勾一项并写明下一项；历史性记录写进 [HISTORY.md](HISTORY.md)，这里只留计划。

## 当前进度

- 正在做：无——「REPRODUCE.md 四步复现核验」已收口（2026-10-12，见 HISTORY.md）
- 下一个：跨厂商家族模型的外部有效性实验（任务 3）

## 任务计划

| # | 任务 | 验收标准（可验证） | 状态 |
|---|---|---|---|
| 1 | ~~修 `test_v06_ci_batch` flaky~~ 复跑 5 连过，证明已不 flaky（2026-10-07，未改动代码） | `pytest tests/test_v06_ci_batch.py` 连续三轮全绿 | 完成 |
| 2 | ~~`docs/REPRODUCE.md` 四步复现挂账清零~~（2026-10-12 完成：90 格 0 错误、指纹过、84/90 格位级一致、6 格漂移根因查明，见 HISTORY.md） | 按该文档跑完四步并记录结果（含机器与耗时） | 完成 |
| 3 | 跨厂商家族模型的外部有效性实验（Roadmap 项） | 至少一个非 Qwen 家族模型按 `--preset published` 完成网格并入 `results/`，`analyze.py --compare-with` 出对比 | 待开始 |
| 4 | audit 小清理（2026-10-12 ponytail-audit 挂账，全部零行为变化）：删 `Candidate` 死字段 `llm_calls/tokens_in/tokens_out/cost_usd`（types.py，全仓无人写）；`_payload_from` 两份逐字相同（batch.py/pr_gate.py）合并进 benchmarks.py；`_mutant_job` 去掉两处调用方都丢弃的 duration；`_maybe_repair` 去掉调用方未用的 `did_repair`；内联单行包装 `_fmt`（client.py）；模块级 `split_candidates` 包装只有测试在用，测试改用 `LLMResponse(...).split_candidates()` 后删除；`analyze.py` 的 `agg["ms_all"]` 去掉包 list 再解包；`new_work_root` 内联进 `workspace`；`cli.py` 的 `__import__(...)` 改函数内常规导入 | 每行改动可追溯到本清单；pytest 89 过 + pyflakes 0 + 离线单格 MS 76.2%/gen 12/acc 2 不漂移；净行数为负 | 完成（2026-10-12，净 -14 行） |
| 5 | ~~`_find_existing_tests` 双份去重裁决~~（2026-10-12 完成：统一口径 = 上两层目录且不越 root，batch 嵌套模块扩为包级超集、pr_gate 根级文件收敛不越仓，见 HISTORY.md） | 先出方案说明（统一成哪个口径、影响面），再合并，pytest/pyflakes 过 | 完成 |
| 6 | `demo_gate_probe` 去留裁决（2026-10-06 登记「留待决断」；2026-10-12 复现核验确认它使 numeric 两目标 6 个已发表格位经 mock 种子漂移） | 二选一并执行：移除（函数自述 Safe to remove，恢复已发表网格逐格位级复现，连带更新 GET-START/AGENTS 单格期望与 benchmarks/README 登记）或保留（AGENTS 已知坑的说明即为最终口径） | 待开始 |

状态取值：待开始 / 进行中 / 待确认 / 完成。

## 完成记录

- [x] 文档九件体系迁移 —— 2026-10-05（见 HISTORY.md 对应条目）
- [x] docs/REPRODUCE.md 四步复现核验 —— 2026-10-12（90 格 0 错误、指纹 (16,6,2,90) 三处一致、84/90 格位级一致、6 格漂移根因 = numeric.py 追加 demo 探针 × mock 种子含模块长度；见 HISTORY.md 对应条目）
