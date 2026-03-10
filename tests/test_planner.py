from iresourcescheduler.domain import ClusterSpec, ClusterState, EstimatedMemory, Vendor
from iresourcescheduler.planner import plan_for_cluster


def test_plan_for_cluster_single_node_tp():
    """
    在 nv-120(L20, 48GB, 8 卡/机) 上, 对 ~173GB 显存需求,
    期望需要 4 卡, 单机 TP 方案可行.
    """
    spec = ClusterSpec(
        cluster_id="nv-120",
        vendor=Vendor.NVIDIA,
        arch="x86",
        gpu_type="L20",
        vram_gb=48,
        nodes=4,
        gpus_per_node=8,
        tags=None,
    )
    state = ClusterState(
        cluster_id="nv-120",
        free_gpus=32,
        free_nodes=4,
        health="healthy",
        maintenance=False,
    )
    estimated = EstimatedMemory(
        required_gb=173.0,
        bytes_per_param=2,
        overhead_factor=1.2,
    )

    plan = plan_for_cluster(spec, state, estimated)

    assert plan.is_feasible is True
    assert plan.required_gpus == 4
    assert plan.required_nodes == 1
    assert plan.multi_node is False
    # 2~8 卡单机应为 TP
    from iresourcescheduler.domain import Parallelism

    assert plan.parallelism == Parallelism.TP

