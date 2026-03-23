"""
从 K8s cardinfo 接口获取集群实时可用资源（PASS_THROUGH 直通卡），
解析为 ClusterState 列表，供调度器使用。

接口说明见 智能资源调度.md「集群实时资源状态（接口）」及项目根目录 api.py。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from iresourcescheduler.domain import ClusterSpec, ClusterState, Vendor

# 接口返回的厂商 key 与本地 Vendor 枚举对应
_API_VENDOR_TO_VENDOR: Dict[str, Vendor] = {
    "Nvidia": Vendor.NVIDIA,
    "Ascend": Vendor.ASCEND,
}

# cardinfo 接口路径（相对 base_url）
CARDINFO_PATH = "/ai/api/v1/k8s/resource/cardinfos"
PASS_THROUGH_KEY = "PASS_THROUGH"
PASS_THROUGH_NODES_KEY = "passThroughNodes"

# 环境变量名：完整的 Authorization 头字段值（勿在代码里写密钥；export 时一并写好整段字符串）
_AUTH_ENV_KEYS = (
    "AUTHORIZATION",
    "Authorization",
    "CARDINFO_API_AUTHORIZATION",
)


def build_cardinfo_authorization_headers(
    api_token: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """
    构造 cardinfo 请求的 Authorization 头，**不从代码硬编码密钥**。

    所有来源的值均为「HTTP Authorization 头的完整字段值」：在 shell 里 ``export`` 时一并写好
    （含 ``Bearer `` 等前缀，若你的网关需要），**代码不会自动拼接 Bearer**。

    优先级:
    1. 环境变量（任选其一）::
           export AUTHORIZATION='...'
           export Authorization='...'
           export CARDINFO_API_AUTHORIZATION='...'
    2. 函数参数 ``api_token``（如 CLI ``--api-token``）：整段 Authorization 值，原样放入请求头
    3. 环境变量 ``CARDINFO_API_TOKEN``：同上，整段值原样放入请求头

    若以上皆无，返回 None（请求将不带 Authorization）。
    """
    for key in _AUTH_ENV_KEYS:
        val = os.environ.get(key, "").strip()
        if val:
            return {"Authorization": val}
    if api_token is not None:
        return {"Authorization": str(api_token).strip()}
    token_only = os.environ.get("CARDINFO_API_TOKEN", "").strip()
    if token_only:
        return {"Authorization": token_only}
    return None


def _parse_pass_through_nodes(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从某卡型下的信息中取出 PASS_THROUGH.passThroughNodes 列表."""
    pt = info.get(PASS_THROUGH_KEY) or {}
    return pt.get(PASS_THROUGH_NODES_KEY) or []


def _aggregate_nodes(nodes: List[Dict[str, Any]]) -> tuple[int, int]:
    """汇总节点列表得到 free_gpus（availableCardNum 之和）和 free_nodes（nodeName 去重个数）."""
    if not nodes:
        return 0, 0
    free_gpus = sum(int(n.get("availableCardNum") or 0) for n in nodes)
    free_nodes = len(set(n.get("nodeName") or "" for n in nodes))
    return free_gpus, free_nodes


def parse_cardinfo_to_states(
    data: Dict[str, Any],
    specs: List[ClusterSpec],
) -> List[ClusterState]:
    """
    将 cardinfo 接口返回的 data 部分解析为 ClusterState 列表。

    仅使用 PASS_THROUGH 模式下的 passThroughNodes；
    通过 (厂商, 卡型) 与 specs 匹配得到 cluster_id。
    """
    states: List[ClusterState] = []
    # 用 (vendor, gpu_type) 快速查找 cluster_id
    spec_by_vendor_gpu: Dict[tuple, ClusterSpec] = {
        (s.vendor, s.gpu_type): s for s in specs
    }

    vendor_data = data or {}
    for api_vendor_key, gpu_type_data in vendor_data.items():
        if not isinstance(gpu_type_data, dict):
            continue
        vendor = _API_VENDOR_TO_VENDOR.get(api_vendor_key)
        if vendor is None:
            continue

        for gpu_type, info in gpu_type_data.items():
            if not isinstance(info, dict):
                continue
            spec = spec_by_vendor_gpu.get((vendor, gpu_type))
            if spec is None:
                # 兼容：API 可能用 "910C" 而配置里是 "Ascend 910C"
                for (v, gt), s in spec_by_vendor_gpu.items():
                    if v == vendor and (gt == gpu_type or gt.endswith(" " + gpu_type)):
                        spec = s
                        break
            if spec is None:
                continue

            nodes = _parse_pass_through_nodes(info)
            free_gpus, free_nodes = _aggregate_nodes(nodes)
            states.append(
                ClusterState(
                    cluster_id=spec.cluster_id,
                    free_gpus=free_gpus,
                    free_nodes=free_nodes,
                    health="healthy",
                    maintenance=False,
                )
            )

    return states


def fetch_cardinfo(
    base_url: str,
    path: str = CARDINFO_PATH,
    headers: Optional[Dict[str, str]] = None,
    proxies: Optional[Dict[str, str]] = None,
    verify: bool = False,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    请求 cardinfo 接口，返回解析后的 JSON 的 data 字段；
    若请求失败或 code != 200，返回空 dict 或抛出。
    """
    try:
        import requests
    except ImportError:
        raise ImportError("需要安装 requests 才能使用 cardinfo 接口: pip install requests")

    url = base_url.rstrip("/") + path
    h = {
        "User-Agent": "yaak",
        "Accept": "*/*",
        **(headers or {}),
    }
    resp = requests.get(
        url,
        headers=h,
        proxies=proxies or {},
        verify=verify,
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 200:
        return {}
    return body.get("data") or {}


def get_cluster_states_from_cardinfo_api(
    specs: List[ClusterSpec],
    base_url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    proxies: Optional[Dict[str, str]] = None,
    verify: bool = False,
) -> List[ClusterState]:
    """
    调用 cardinfo 接口，将返回解析为与 specs 对应的 ClusterState 列表。
    未配置 base_url 或请求失败时抛出异常，不再静默回退。

    - base_url: 接口根地址（如 https://your-ip）；不传则从环境变量 CARDINFO_API_BASE_URL 读取。
    - headers: 可包含 Authorization；未传时由 build_cardinfo_authorization_headers 从环境变量解析。
    """
    base_url = base_url or os.environ.get("CARDINFO_API_BASE_URL", "").strip()
    if not base_url:
        raise ValueError(
            "CARDINFO_API_BASE_URL 未设置，无法请求 cardinfo 接口。"
        )

    h = dict(headers or {})
    if not str(h.get("Authorization", "")).strip():
        extra = build_cardinfo_authorization_headers(api_token=None)
        if extra:
            h.update(extra)

    try:
        data = fetch_cardinfo(
            base_url=base_url,
            headers=h,
            proxies=proxies,
            verify=verify,
        )
    except Exception as e:
        raise RuntimeError(
            f"cardinfo 接口请求失败: {base_url}{CARDINFO_PATH} — {e!s}"
        ) from e

    return parse_cardinfo_to_states(data, specs)
