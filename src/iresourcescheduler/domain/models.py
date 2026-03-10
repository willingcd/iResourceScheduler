from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any


class Vendor(str, Enum):
    ASCEND = "ascend"
    NVIDIA = "nvidia"


class Parallelism(str, Enum):
    NONE = "none"
    TP = "tp"
    TP_PP = "tp+pp"


@dataclass
class ScheduleRequest:
    """调度请求的标准输入."""

    model_id: str
    model_params_b: float  # 官方参数量, 单位: B (billion)
    engine: str
    arch_requirement: str = "any"  # "any" / "ascend" / "nvidia" / 具体架构字符串
    extra_hints: Optional[Dict[str, Any]] = None


@dataclass
class ClusterSpec:
    """集群静态规格."""

    cluster_id: str
    vendor: Vendor
    arch: str  # arm / x86 / others
    gpu_type: str
    vram_gb: float
    nodes: int
    gpus_per_node: int
    tags: Optional[Dict[str, Any]] = None


@dataclass
class ClusterState:
    """集群动态状态."""

    cluster_id: str
    free_gpus: int
    free_nodes: int
    health: str = "healthy"  # healthy / degraded / down
    maintenance: bool = False


@dataclass
class EstimatedMemory:
    """显存估算结果."""

    required_gb: float
    bytes_per_param: int
    overhead_factor: float


@dataclass
class Plan:
    """在某个集群上的资源使用计划."""

    cluster_spec: ClusterSpec
    cluster_state: ClusterState
    estimated_memory: EstimatedMemory

    required_gpus: int
    required_nodes: int
    parallelism: Parallelism
    multi_node: bool
    is_feasible: bool
    reason: str


@dataclass
class Decision:
    """对外暴露的调度决策输出."""

    cluster_id: str
    gpu_type: str
    gpu_count: int
    node_count: int
    parallelism: Parallelism
    multi_node: bool
    needs_manual_intervention: bool = False
    meta: Optional[Dict[str, Any]] = None


@dataclass
class FailureEvent:
    """统一失败事件, 用于失败处理/通知."""

    code: str
    message: str
    context: Optional[Dict[str, Any]] = None

