from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.estimator import estimate_memory


def test_estimate_memory_basic():
    """
    72B 模型在默认 BF16 + 1.2 开销下, 显存估算应为一个正数且大于 0.
    """
    req = ScheduleRequest(
        model_id="Qwen/Qwen3-72B",
        model_params_b=72,
        engine="vllm",
        arch_requirement="any",
    )

    estimated = estimate_memory(req)

    assert estimated.required_gb > 0
    # 大致数量级 sanity check: 72B * 2 * 1.2 / 1e9 ~= 173GB
    assert 150 <= estimated.required_gb <= 200

