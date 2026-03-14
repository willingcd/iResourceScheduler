"""解析 cardinfo 接口返回的 data 为 ClusterState 列表."""
from iresourcescheduler.domain import ClusterSpec, Vendor
from iresourcescheduler.inventory import parse_cardinfo_to_states


def test_parse_cardinfo_to_states_nvidia_l20():
    """Nvidia L20 的 PASS_THROUGH 节点被汇总为 free_gpus / free_nodes."""
    specs = [
        ClusterSpec(
            cluster_id="nv-120",
            vendor=Vendor.NVIDIA,
            arch="x86",
            gpu_type="L20",
            vram_gb=48,
            nodes=4,
            gpus_per_node=8,
            tags=None,
        ),
    ]
    data = {
        "Nvidia": {
            "L20": {
                "PASS_THROUGH": {
                    "passThroughNodes": [
                        {"nodeName": "work1", "slots": ["13"], "availableCardNum": 1},
                        {"nodeName": "work2", "slots": ["0", "1"], "availableCardNum": 2},
                    ]
                }
            }
        }
    }
    states = parse_cardinfo_to_states(data, specs)
    assert len(states) == 1
    assert states[0].cluster_id == "nv-120"
    assert states[0].free_gpus == 3
    assert states[0].free_nodes == 2
    assert states[0].health == "healthy"

