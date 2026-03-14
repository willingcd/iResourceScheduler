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
    "CardinfoNotConfiguredError",
]


class CardinfoNotConfiguredError(ValueError):
    """未配置 cardinfo 接口时抛出。"""


def get_cluster_states(
    specs: List[ClusterSpec],
    base_url: Optional[str] = None,
    headers: Optional[dict] = None,
    use_api: Optional[bool] = None,
) -> List[ClusterState]:
    """
    获取各集群当前状态。必须使用真实 cardinfo 接口，未配置时报错。

    - specs: ClusterSpec 列表（用于 API 时做 厂商/卡型 -> cluster_id 映射）。
    - base_url: 可选，cardinfo 接口根地址；不传则读环境变量 CARDINFO_API_BASE_URL。
    - headers: 可选，请求头（如 Authorization）。
    - use_api: True 或 None 时必须配置接口；False 时使用 mock。环境变量 IRESCHEDULER_USE_MOCK_STATE=1 时也使用 mock（供测试用）。
    """
    if use_api is False or os.environ.get("IRESCHEDULER_USE_MOCK_STATE") == "1":
        return get_cluster_states_mock([s.cluster_id for s in specs])
    url = (base_url or "").strip() or os.environ.get("CARDINFO_API_BASE_URL", "").strip()
    if not url:
        raise CardinfoNotConfiguredError(
            "未配置 cardinfo 接口。请设置环境变量 CARDINFO_API_BASE_URL（如 https://your-ip），"
            "或调用时传入 base_url。仅本地测试可传 use_api=False 使用 mock。"
        )
    return get_cluster_states_from_cardinfo_api(
        specs, base_url=base_url or url or None, headers=headers
    )

