import os
from typing import List, Optional

from iresourcescheduler.domain import ClusterSpec, ClusterState

from .specs_loader import load_cluster_specs
from .state_mock import get_cluster_states_mock
from .state_cardinfo import (
    get_cluster_states_from_cardinfo_api,
    parse_cardinfo_to_states,
)

__all__ = [
    "load_cluster_specs",
    "get_cluster_states_mock",
    "get_cluster_states_from_cardinfo_api",
    "parse_cardinfo_to_states",
    "get_cluster_states",
]


def get_cluster_states(
    specs: List[ClusterSpec],
    base_url: Optional[str] = None,
    headers: Optional[dict] = None,
    use_api: Optional[bool] = None,
) -> List[ClusterState]:
    """
    获取各集群当前状态。若配置了 cardinfo 接口则走 API，否则用 mock。

    - specs: ClusterSpec 列表（用于 API 时做 厂商/卡型 -> cluster_id 映射）。
    - base_url: 可选，cardinfo 接口根地址；不传则读环境变量 CARDINFO_API_BASE_URL。
    - headers: 可选，请求头（如 Authorization）。
    - use_api: True 强制用 API，False 强制用 mock；None 时根据 base_url 或环境变量决定。
    """
    if use_api is False:
        return get_cluster_states_mock([s.cluster_id for s in specs])
    url = (base_url or "").strip() or os.environ.get("CARDINFO_API_BASE_URL", "").strip()
    if use_api is True or url:
        states = get_cluster_states_from_cardinfo_api(
            specs, base_url=base_url or url or None, headers=headers
        )
        if states:
            return states
    return get_cluster_states_mock([s.cluster_id for s in specs])

