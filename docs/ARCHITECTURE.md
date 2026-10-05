# TestForge 架构

> 用途：给要理解或改动本仓结构的人。架构总览、模块职责、数据组织方式、关键约定都在这里。
> 操作步骤在 `docs/GET-START.md`；数字口径在根目录 `AGENTS.md` 的「当前状态」。

## 架构总览

Python CLI + 实验框架：给一个函数，LLM 生成候选单元测试，只有稳定通过原代码、且至少杀死一个
"既有测试杀不死的变异体"的候选才被收进套件。回路编排（`agent/orchestrator.py`：基线 → 变异 →
生成 → 门禁 → 联合评估）串起四个子系统：`analysis/`（目标静态解析）、`mutation/`（7 类算子 +
杀伤矩阵进程池）、`llm/`（Mock / OpenAI 兼容双后端 + 磁盘缓存）、`gate/`（多信号验收）。
0.6 起加落地外壳：`pr_gate.py`（`ci` 子命令）与 `batch.py`（`batch` 子命令）复用同一条回路。

## 目录结构与各文件职责

| 路径 | 职责 | 关键文件 |
|---|---|---|
| `testforge/cli.py` | 命令行入口 | `_cmd_run`：读配置 → 取变体 → 解析目标 → 跑 → 落盘 |
| `testforge/budget.py` | 硬预算（墙钟/token） | 耗尽时生成循环干净停止、联合评估照跑（`VariantResult.budget_exceeded`） |
| `testforge/diff_targets.py` | diff→改动函数 | `parse_diff` + `changed_functions`；纯删除不产目标 |
| `testforge/pr_gate.py` | PR 质量门禁流程 | 退出码非 0 仅限基础设施错误（低分是信息不是失败） |
| `testforge/batch.py` | 整仓批量增强 | 优先级队列：无测试优先→测试少→名字序 |
| `testforge/config.py` | 全部旋钮 + 零依赖 `.env` 读取 | 缺 key 时 `SystemExit` |
| `testforge/variants.py` | 实验条件 B0–B5 定义 | `VARIANTS`：rounds / gate_enabled / feedback_mode / continue_on_zero_accept |
| `testforge/mutation/engine.py` | 变异体生成与采样 | `priority=True` PRIMG 式优先（默认关）；`runner.py` 增量执行（未覆盖行免跑） |
| `testforge/types.py` | 共享数据结构 | `Outcome.killed_mutant`；`ms_all`/`ms_covered` 为派生属性 |
| `testforge/agent/` | 回路编排与 prompt | `orchestrator.py` 的 `run_target`；`prompts.py`（`=== BLOCK ===` 结构） |
| `testforge/gate/` | 验收判定与原代码执行 | `evaluate_candidate` / `run_tests_once` / `measure_coverage` |
| `testforge/mutation/` | 变异体生成与杀伤矩阵 | `operators.py`（7 类算子）、`runner.py`（进程池 + `pytest -x`） |
| `testforge/llm/` | 两个后端 | `OpenAICompatClient`（双传输/磁盘缓存/重试/节流/记账）与 `MockLLMClient` |
| `testforge/analysis/` | 目标函数静态解析 | `inspector.py` |
| `testforge/report/` | Markdown 渲染 | `render_target_report` / `render_summary` |
| `testforge/utils.py` | 临时工作区、子进程、diff、JSON | `workspace()` 退出即删；`run_cmd()` 超时返回 -9 |
| `benchmarks/` | 目标函数 + 每模块一份既有测试（B0） | `manifest.json` 是目标清单的唯一来源 |
| `experiments/` | 网格、统计、图、跨网格比较 | `run_experiment.py` / `analyze.py` / `plots.py` / `compare_grids.py` |
| `tests/` | 自身测试 | 13 个文件、91 项，见 `tests/README.md` |
| `results/` | 实验产物 | 只读；`.gitignore` 白名单只放行 `results/exp_*` 的 JSON/MD/PNG |
| `action.yml` | 仓库即 GitHub Action（composite） | 任何仓库 `uses: Luz7818/testforge@v0.6.0` |

## 数据组织方式

- **逐格落盘、可续跑**：`run_experiment.py` 每跑完一格就重写整份 `results.json`；重启时已完成格
  打印 `skip (cached)`；带 `error` 键的格移出到同目录 `errors.json` 后重跑（27B 主网格首跑撞
  HTTP 420 限流丢 36 格，靠续跑补齐）。
- **prompt 磁盘缓存**：`llm_cache/` 根部 = 默认缓存；五个子目录（`27b_full` 等）= 历次真实网格
  的独立采样缓存（2026-10-05 从根部散目录收拢）。缓存键含 `TESTFORGE_EXTRA_BODY`。命中即
  零 API 消耗、逐位重放；独立采样 = 缓存目录指到空目录。Mock 后端不读写缓存。
- **实验产物的数字口径**："36 个单元"/"pooled n=36" 指实验格数（18 目标 × 2 轮网格），
  不是测试数（91）；两处不要互相引用。
- `results/exp_mock_full/analysis.md` 是旧脚本产物，重算版在同目录 `analysis_v2.md`；
  `docs/example-report.md` 来自已跟踪的 `results/api_smoke/` 渲染，克隆后无法重跑该核对。

## 关键约定（违反会出问题的）

1. **确定性用 `zlib.crc32`，不用内建 `hash()`**（`orchestrator._stable_hash`、Mock 测试名后缀）：
   内建 hash 按进程加盐（`PYTHONHASHSEED`），换进程就换一批变异体，网格不可复现。
2. **缓存键即 prompt 指纹**：改键构成 = 换 prompt 语义；不要手改 `llm_cache/` 文件名或内容。
3. **逐格落盘 + 续跑**：错误格归档 `errors.json` 后重跑同一命令只补错误格；长限流窗口不要指望
   进程内重试。
4. **变异体分层采样**：超 `max_mutants`（默认 24）按算子分组轮转、组内种子洗牌——保算子多样性。
   每格种子 = `mutation_seed + crc32(target_id) % 10000`；编号 `M001…` 采样后按行号重排，换上限
   即换编号。
5. **B0 是模块级的**：一个模块的整份测试文件同时用于该模块三个目标。
6. **早退规则**：B3 零验收即退，B5 把轮次预算走完——改这条会直接改动 RQ5 的对照定义。
7. **杀伤口径**：pytest 退出码 0 和 5 都算 PASS（5 = 未收集到用例，靠可证伪性门禁挡在外面），
   1 为 FAIL，-9 为 TIMEOUT；TIMEOUT 计为杀死。验收看 `falsifiable`，不是覆盖率。
8. **`n_accepted` 是最终套件文件数**：联合评估不过会按"和 B0 一起跑不过"逐个剔除（最多三轮），
   可能小于回路中验收数。
9. **登记闸门**：加新目标函数会让 `tests/test_inspector.py` 的"18 个目标"断言失败——改基准必须
   同步改断言。

## 子目录说明索引

| 子目录 | 说明 |
|---|---|
| `testforge/` | [testforge/README.md](../testforge/README.md) |
| `benchmarks/` | 目标函数与 B0 既有测试（清单见 `manifest.json`） |
| `experiments/` | [experiments/README.md](../experiments/README.md)（网格与冒烟） |
| `tests/` | [tests/README.md](../tests/README.md) |
| `results/` | 只读实验产物（白名单入库） |
| `docs/` | 无（文档目录本身） |

## 已知架构问题

- 效果结论受模型与基准覆盖限制：单一模型（qwen3.8-27B）、18 个确定性纯函数、单一语言；
  等价变异体无法穷尽排除，变异分数是下界（详见 `docs/report.md`）。
- 跨厂商家族模型支持在 Roadmap 上（`TODO.md`）。
