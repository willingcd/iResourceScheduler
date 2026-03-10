from __future__ import annotations

from datetime import datetime, timezone
from typing import List
import json

from iresourcescheduler.domain import ScheduleRequest, EstimatedMemory, Decision


def log_decision(
    request: ScheduleRequest,
    estimated: EstimatedMemory,
    decisions: List[Decision],
) -> None:
    """
    简单的决策日志实现: 以 JSON 形式打印到终端.
    后续可以改为写文件或接入日志系统.
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": request.model_id,
        "model_params_b": request.model_params_b,
        "estimated_memory_gb": estimated.required_gb,
        "engine": request.engine,
        "arch_requirement": request.arch_requirement,
        "decisions": [
            {
                "cluster_id": d.cluster_id,
                "gpu_type": d.gpu_type,
                "gpu_count": d.gpu_count,
                "node_count": d.node_count,
                "parallelism": d.parallelism.value,
                "multi_node": d.multi_node,
                "needs_manual_intervention": d.needs_manual_intervention,
                "meta": d.meta or {},
            }
            for d in decisions
        ],
    }
    print("[DECISION]", json.dumps(payload, ensure_ascii=False))

