from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from iresourcescheduler.domain import ClusterSpec, Vendor


def load_cluster_specs(config_path: Path | None = None) -> List[ClusterSpec]:
    """
    从 YAML 配置加载集群规格列表.
    """
    if config_path is None:
        # 默认相对于当前文件的 clusters.yaml
        config_path = Path(__file__).with_name("clusters.yaml")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    clusters: list[ClusterSpec] = []
    for item in data.get("clusters", []):
        clusters.append(
            ClusterSpec(
                cluster_id=item["cluster_id"],
                vendor=Vendor(item["vendor"]),
                arch=item["arch"],
                gpu_type=item["gpu_type"],
                vram_gb=float(item["vram_gb"]),
                nodes=int(item["nodes"]),
                gpus_per_node=int(item["gpus_per_node"]),
                tags=item.get("tags") or {},
            )
        )
    return clusters

