# TODO —— 开发计划与当前进度

> 用途：给开发者与 AI。当前在做哪个任务、每个任务按什么标准验收、接下来做什么。
> 完成一项就勾一项并写明下一项；历史性记录写进 [HISTORY.md](HISTORY.md)，这里只留计划。

## 当前进度

- 正在做：无——「文档与实际数字全仓同步」批已收口（2026-10-06，见 HISTORY.md）
- 下一个：`docs/REPRODUCE.md` 四步复现挂账清零（任务 2）

## 任务计划

| # | 任务 | 验收标准（可验证） | 状态 |
|---|---|---|---|
| 1 | ~~修 `test_v06_ci_batch` flaky~~ 复跑 5 连过，证明已不 flaky（2026-10-07，未改动代码） | `pytest tests/test_v06_ci_batch.py` 连续三轮全绿 | 完成 |
| 2 | `docs/REPRODUCE.md` 四步复现挂账清零（核查报告 P2 延续） | 按该文档跑完四步并记录结果（含机器与耗时） | 待开始 |
| 3 | 跨厂商家族模型的外部有效性实验（Roadmap 项） | 至少一个非 Qwen 家族模型按 `--preset published` 完成网格并入 `results/`，`analyze.py --compare-with` 出对比 | 待开始 |
| 4 | audit 小清理（2026-10-12 ponytail-audit 挂账，全部零行为变化）：删 `Candidate` 死字段 `llm_calls/tokens_in/tokens_out/cost_usd`（types.py，全仓无人写）；`_payload_from` 两份逐字相同（batch.py/pr_gate.py）合并进 benchmarks.py；`_mutant_job` 去掉两处调用方都丢弃的 duration；`_maybe_repair` 去掉调用方未用的 `did_repair`；内联单行包装 `_fmt`（client.py）；模块级 `split_candidates` 包装只有测试在用，测试改用 `LLMResponse(...).split_candidates()` 后删除；`analyze.py` 的 `agg["ms_all"]` 去掉包 list 再解包；`new_work_root` 内联进 `workspace`；`cli.py` 的 `__import__(...)` 改函数内常规导入 | 每行改动可追溯到本清单；pytest 89 过 + pyflakes 0 + 离线单格 MS 76.2%/gen 8/acc 2 不漂移；净行数为负 | 待开始 |
| 5 | `_find_existing_tests` 双份去重裁决（batch.py 与 pr_gate.py 近似重复但父目录遍历语义不同：batch 找 `module_path.parent`，pr_gate 找 `parent.parent`，合并会改其中一侧行为） | 先出方案说明（统一成哪个口径、影响面），再合并，pytest/pyflakes 过 | 待开始 |

状态取值：待开始 / 进行中 / 待确认 / 完成。

## 完成记录

- [x] 文档九件体系迁移 —— 2026-10-05（见 HISTORY.md 对应条目）
