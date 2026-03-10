from __future__ import annotations

from .typing import ScheduleRequest, EstimatedMemory

# 为简单起见, 默认 BF16 精度: 2 bytes/param, 开销系数 1.2
DEFAULT_BYTES_PER_PARAM = 2
DEFAULT_OVERHEAD_FACTOR = 1.2


def _parse_params_b(params_b: float) -> float:
    """将官方参数量(单位 B)转换为精确的浮点数表示."""
    # 直接乘以 1e9, 例如 72B -> 72e9
    return float(params_b) * 1e9


def estimate_memory(
    request: ScheduleRequest,
    bytes_per_param: int = DEFAULT_BYTES_PER_PARAM,
    overhead_factor: float = DEFAULT_OVERHEAD_FACTOR,
) -> EstimatedMemory:
    """
    根据模型参数量估算显存需求(GB).

    显存需求(GB) = params * bytes_per_param * overhead_factor / 1e9
    """
    total_params = _parse_params_b(request.model_params_b)
    required_bytes = total_params * bytes_per_param * overhead_factor
    required_gb = required_bytes / 1e9

    return EstimatedMemory(
        required_gb=required_gb,
        bytes_per_param=bytes_per_param,
        overhead_factor=overhead_factor,
    )

