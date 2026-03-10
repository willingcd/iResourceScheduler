from __future__ import annotations

from typing import List

from iresourcescheduler.domain import ClusterState


def get_cluster_states_mock(cluster_ids: list[str]) -> List[ClusterState]:
    """
    简单的集群状态 mock:
    - 所有集群都健康且无维护;
    - free_gpus/free_nodes 取一个“看起来足够大”的固定值.
    """
    states: list[ClusterState] = []
    for cid in cluster_ids:
        states.append(
            ClusterState(
                cluster_id=cid,
                free_gpus=64,
                free_nodes=8,
                health="healthy",
                maintenance=False,
            )
        )
    return states

