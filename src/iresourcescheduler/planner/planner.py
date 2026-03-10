from __future__ import annotations

import math
from typing import Optional

from iresourcescheduler.domain import (
    ClusterSpec,
    ClusterState,
    EstimatedMemory,
    Plan,
    Parallelism,
)


def _effective_vram(vram_gb: float, ratio: float) -> float:
    return vram_gb * ratio


def plan_for_cluster(
    spec: ClusterSpec,
    state: ClusterState,
    estimated: EstimatedMemory,
    effective_ratio: float = 0.98,
    allow_multi_node: bool = True,
) -> Plan:
    """
    为某个集群生成资源计划:
    - 计算单卡可用显存 -> 所需卡数 -> 所需节点数;
    - 决定单机/多机 & 并行策略;
    - 校验资源是否足够, 标记 is_feasible.
    """
    eff_vram = _effective_vram(spec.vram_gb, effective_ratio)
    if eff_vram <= 0:
        return Plan(
            cluster_spec=spec,
            cluster_state=state,
            estimated_memory=estimated,
            required_gpus=0,
            required_nodes=0,
            parallelism=Parallelism.NONE,
            multi_node=False,
            is_feasible=False,
            reason="effective_vram_non_positive",
        )

    required_gpus = int(math.ceil(estimated.required_gb / eff_vram))
    if required_gpus <= 0:
        required_gpus = 1

    gpus_per_node = spec.gpus_per_node
    required_nodes = int(math.ceil(required_gpus / gpus_per_node))

    # 单机 / 多机 + 并行策略
    if required_gpus <= gpus_per_node:
        multi_node = False
        if required_gpus == 1:
            parallelism = Parallelism.NONE
        else:
            parallelism = Parallelism.TP
    else:
        multi_node = True
        parallelism = Parallelism.TP_PP

    # 资源校验
    if state.health != "healthy" or state.maintenance:
        feasible = False
        reason = "cluster_unhealthy_or_maintenance"
    elif multi_node and not allow_multi_node:
        feasible = False
        reason = "multi_node_not_allowed"
    elif state.free_gpus < required_gpus or state.free_nodes < required_nodes:
        feasible = False
        reason = "insufficient_resources"
    else:
        feasible = True
        reason = "ok"

    return Plan(
        cluster_spec=spec,
        cluster_state=state,
        estimated_memory=estimated,
        required_gpus=required_gpus,
        required_nodes=required_nodes,
        parallelism=parallelism,
        multi_node=multi_node,
        is_feasible=feasible,
        reason=reason,
    )

