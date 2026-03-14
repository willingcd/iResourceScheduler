### iResourceScheduler v1

智能 GPU 资源调度器（MVP 版本），根据模型参数量、推理引擎和架构要求，在异构集群上自动生成可运行的资源方案。

当前支持：

- 集群类型：Ascend 910C / 910B3、NVIDIA L20 / H20（静态配置见 `src/iresourcescheduler/inventory/clusters.yaml`）
- 输入：模型官方参数量 `params_b`（单位 B）、引擎名称、架构要求（any / ascend / nvidia）
- 输出：一个或多个 `Decision`（集群 ID + 卡型 + 卡数 + 机器数 + 并行策略），以及终端上的决策/失败日志

---

### 目录结构概览

- `pyproject.toml`：Python 包配置（包名 `iresourcescheduler`，依赖 PyYAML）
- `智能资源调度.md`：调度策略设计说明
- `调度代码流程图.md`：详细代码流程图（Mermaid）
- `调度代码大纲流程图.md`：粗略代码大纲流程图
- `src/iresourcescheduler/`
  - `domain/`：核心数据模型
    - `models.py`：`ScheduleRequest`、`ClusterSpec`、`ClusterState`、`EstimatedMemory`、`Plan`、`Decision`、`FailureEvent` 等
  - `estimator/`：显存估算
    - `memory_estimator.py`：`estimate_memory(request)`，基于 `params_b` + BF16 + 1.2 开销系数估算显存需求
  - `inventory/`：集群静态配置 + 集群状态获取
    - `clusters.yaml`：当前 4 个集群的规格（显存、机器数、卡数）
    - `specs_loader.py`：`load_cluster_specs()`，从 YAML 读静态配置
    - `state_mock.py`：`get_cluster_states_mock()`，简单的 mock 资源状态
    - `state_cardinfo.py`：从 K8s **cardinfo 接口**获取实时可用资源（仅解析 PASS_THROUGH 节点），`get_cluster_states_from_cardinfo_api()` / `parse_cardinfo_to_states()`；调度器通过 `get_cluster_states(specs)` 自动在「配置了接口时走 API、否则 mock」之间切换
  - `compatibility/`：兼容性规则
    - `rules.py`：`filter_compatible_clusters()`，按引擎/架构筛选候选集群
  - `planner/`：单集群资源规划
    - `planner.py`：`plan_for_cluster()`，计算所需卡数/机器数、并行策略（NONE/TP/TP+PP），并判断是否可行  
      默认单卡可用显存使用 `effective_ratio = 0.98`（预留 2% 余量）
  - `scheduler/`：调度主流程
    - `scheduler.py`：`schedule(request)`，串联估算 -> 加载配置 -> 获取状态 -> 兼容性过滤 -> 规划 Plan -> 过滤不可行 -> 同构去重 -> 生成 Decisions -> 记录日志或失败通知
  - `logging/`：日志与失败处理
    - `decision_logger.py`：`log_decision()`，在终端打印 `[DECISION] {...}` JSON 日志
    - `failure_handler.py`：`handle_failure()`，在终端打印 `[SCHEDULER_FAILURE_NOTIFY] {...}`，预留为未来「发通知到 app」的统一入口
  - `cli/`
    - `main.py`：简单 CLI 入口，命令行调用调度流程
- `tests/`
  - `test_estimator.py`：显存估算单测
  - `test_planner.py`：单集群规划逻辑单测（例如 72B + L20 ≈ 4 卡 TP）
  - `test_scheduler.py`：调度主流程单测

---

### 环境准备

在项目根目录（本文件所在目录）下：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate

pip install -e .
```

这会安装：

- 包本身：`iresourcescheduler`
- 依赖：`PyYAML`、`requests`（用于 cardinfo 接口）

建议同时安装开发依赖（pytest 等）：

```bash
pip install pytest
```

---

### 集群状态来源：mock 与 cardinfo 接口

- **默认**：未配置接口时，调度器使用 `get_cluster_states_mock()`，各集群返回固定“资源充足”的假数据。
- **接入真实资源**：设置环境变量后，调度器会调用 **cardinfo 接口**（与项目根目录 `api.py` 中一致），仅使用 **PASS_THROUGH** 模式下的 `passThroughNodes`，汇总得到各集群的 `free_gpus`、`free_nodes`。
  - `CARDINFO_API_BASE_URL`：接口根地址，例如 `https://your-ip`（不要带路径，内部会拼 `/ai/api/v1/k8s.resource/cardinfos`）。
  - `CARDINFO_API_TOKEN`：可选，Bearer Token，未设置则需在代码里通过 `get_cluster_states(specs, headers={...})` 传入 Authorization。
- 在代码中也可直接调用 `get_cluster_states(specs, base_url=..., use_api=True)` 强制走 API，或 `use_api=False` 强制 mock。

---

### 核心使用方式（作为 Python 库）

在你的 Python 代码中：

```python
from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.scheduler import schedule

req = ScheduleRequest(
    model_id="Qwen/Qwen3-72B",
    model_params_b=72,     # 官方参数量: 72B
    engine="vllm",         # 推理引擎
    arch_requirement="any" # 或 "ascend" / "nvidia"
)

decisions = schedule(req)

for d in decisions:
    print(
        d.cluster_id,
        d.gpu_type,
        d.gpu_count,
        d.node_count,
        d.parallelism.value,
        d.multi_node,
    )
```

运行时行为：

- 若存在可行方案：
  - `schedule()` 返回一个 `Decision` 列表（同构方案去重、不同构方案全部保留）
  - 终端会输出一条 `[DECISION] {...}` JSON 日志，方便审计
- 若无任何可行方案（无兼容集群 / 资源不足等）：
  - `schedule()` 返回空列表
  - 终端会输出一条 `[SCHEDULER_FAILURE_NOTIFY] {...}` JSON 日志，模拟未来的「发送通知到 app」行为

---

### 使用 CLI 调度

项目根目录下（确保虚拟环境已激活并安装了本包）：

```bash
PYTHONPATH=src python -m iresourcescheduler.cli.main \
  --model-id Qwen/Qwen3-72B \
  --model-params-b 72 \
  --engine vllm \
  --arch-requirement any
```

输出包括：

- 一条或多条 `[DECISION] {...}` 日志（记录完整调度信息）
- 最后一段是格式化的 `Decision` 列表 JSON，方便在终端直接查看

---

### 运行测试

在项目根目录执行：

```bash
pytest
```

目前的测试覆盖：

- 显存估算是否在合理区间（例如 72B ≈ 173GB）
- 在 nv-120 (L20) 上针对 ~173GB 需求是否得到「4 卡 TP 单机」的可行方案
- `schedule()` 在典型场景（72B vllm any）能否返回非空 Decision 列表
- 对极端大模型（远超现有资源）是否返回空列表并触发失败处理

---

### 后续扩展方向（预留点）

- **集群状态**：已支持通过 cardinfo 接口（`CARDINFO_API_BASE_URL`）获取实时 PASS_THROUGH 资源；可再接入其他 K8s/Slurm 数据源或扩展 SHARED 模式解析。
- **更精细的显存模型**：按引擎、精度（BF16/FP8/INT8/INT4）、上下文长度等维度调整估算公式。
- **更多调度策略**：
  - 支持队列/排队（当前只做“是否可立即调度”的判断）
  - 更复杂的并行策略选择（TP degree / PP degree 显式输出）
- **通知通道**：在 `logging.failure_handler.handle_failure` 中接入实际的 App 通知 / Webhook / IM 机器人。

