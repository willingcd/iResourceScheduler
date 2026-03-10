from __future__ import annotations

from typing import List

from iresourcescheduler.domain import ClusterSpec, ScheduleRequest, Vendor


def _engine_vendor_hint(engine: str) -> str:
    """
    根据 engine 名字给出一个粗略的 vendor 偏好:
    - 包含 ascend: ascend
    - 包含 nvidia/cuda/trt: nvidia
    - 否则: any
    """
    e = engine.lower()
    if "ascend" in e or "910" in e:
        return "ascend"
    if "nvidia" in e or "cuda" in e or "trt" in e:
        return "nvidia"
    return "any"


def filter_compatible_clusters(
    request: ScheduleRequest,
    specs: List[ClusterSpec],
) -> List[ClusterSpec]:
    """
    按引擎 / 架构要求过滤候选集群.

    规则:
    - arch_requirement 为 ascend/nvidia 时, 只保留对应 vendor;
    - 否则根据 engine 推断 vendor 偏好; 若为 any, 不按 vendor 限制;
    - 若有特定 arch(arm/x86) 要求, 可进一步过滤 (目前仅示例, 默认不过滤).
    """
    desired_vendor: str
    if request.arch_requirement in ("ascend", "nvidia"):
        desired_vendor = request.arch_requirement
    else:
        desired_vendor = _engine_vendor_hint(request.engine)

    result: list[ClusterSpec] = []
    for spec in specs:
        # vendor 过滤
        if desired_vendor == "ascend" and spec.vendor is not Vendor.ASCEND:
            continue
        if desired_vendor == "nvidia" and spec.vendor is not Vendor.NVIDIA:
            continue

        # TODO: 若后续有更细的架构要求 (arm/x86), 可在此补充
        result.append(spec)

    return result

