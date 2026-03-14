from __future__ import annotations

from typing import List

from iresourcescheduler.compatibility import filter_compatible_clusters
from iresourcescheduler.domain import (
    ScheduleRequest,
    Plan,
    Decision,
    FailureEvent,
)
from iresourcescheduler.estimator import estimate_memory
from iresourcescheduler.inventory import load_cluster_specs, get_cluster_states
from iresourcescheduler.logging import log_decision, handle_failure
from iresourcescheduler.planner import plan_for_cluster


def _build_decisions_from_plans(plans: List[Plan]) -> List[Decision]:
    """
    将所有可行的 Plan 转换为 Decision 列表.

    当前实现:
    - 简单按 cluster_id + gpu_type + required_gpus + required_nodes + parallelism 去重,
      视作“同构配置”只保留一份;
    - 不对“不同构”方案做筛减.
    """
    seen_keys: set[tuple] = set()
    decisions: list[Decision] = []

    for p in plans:
        if not p.is_feasible:
            continue

        key = (
            p.cluster_spec.vendor.value,
            p.cluster_spec.arch,
            p.cluster_spec.gpu_type,
            p.required_gpus,
            p.required_nodes,
            p.parallelism.value,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)

        decisions.append(
            Decision(
                cluster_id=p.cluster_spec.cluster_id,
                gpu_type=p.cluster_spec.gpu_type,
                gpu_count=p.required_gpus,
                node_count=p.required_nodes,
                parallelism=p.parallelism,
                multi_node=p.multi_node,
                needs_manual_intervention=p.multi_node,
                meta={
                    "reason": p.reason,
                    "estimated_memory_gb": p.estimated_memory.required_gb,
                },
            )
        )

    return decisions


def schedule(request: ScheduleRequest) -> List[Decision]:
    """
    调度主入口.

    步骤:
    1. 显存估算;
    2. 加载集群规格;
    3. 获取集群状态(当前使用 mock);
    4. 按引擎/架构过滤候选集群;
    5. 为每个候选集群生成 Plan;
    6. 过滤不可行 Plan;
    7. 对可行 Plan 做同构去重, 生成 Decisions;
    8. 写决策日志; 如无任何可行方案, 统一失败处理.
    """
    # 1. 显存估算
    estimated = estimate_memory(request)

    # 2. 加载集群规格
    specs = load_cluster_specs()
    if not specs:
        event = FailureEvent(
            code="NO_CLUSTER_SPECS",
            message="No cluster specs loaded",
            context={},
        )
        handle_failure(event)
        return []

    # 3. 获取集群状态（若配置 CARDINFO_API_BASE_URL 则走 cardinfo 接口，否则 mock）
    states = get_cluster_states(specs)
    state_map = {s.cluster_id: s for s in states}

    # 4. 过滤候选集群
    candidates = filter_compatible_clusters(request, specs)
    if not candidates:
        event = FailureEvent(
            code="NO_COMPATIBLE_CLUSTERS",
            message="No compatible clusters for request",
            context={
                "engine": request.engine,
                "arch_requirement": request.arch_requirement,
            },
        )
        handle_failure(event)
        return []

    # 5. 为每个候选集群生成 Plan
    plans: list[Plan] = []
    for spec in candidates:
        state = state_map.get(spec.cluster_id)
        if state is None:
            # 没有状态信息视为不可用
            continue
        plan = plan_for_cluster(spec, state, estimated)
        plans.append(plan)

    # 6. 过滤不可行 Plan
    feasible_plans = [p for p in plans if p.is_feasible]
    if not feasible_plans:
        event = FailureEvent(
            code="NO_FEASIBLE_PLAN",
            message="No feasible plans for request",
            context={
                "engine": request.engine,
                "arch_requirement": request.arch_requirement,
                "estimated_memory_gb": estimated.required_gb,
            },
        )
        handle_failure(event)
        return []

    # 7. 生成 Decisions (同构去重, 异构保留)
    decisions = _build_decisions_from_plans(feasible_plans)

    # 8. 记录决策日志
    log_decision(request, estimated, decisions)

    return decisions

