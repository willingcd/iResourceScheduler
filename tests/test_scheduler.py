from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.scheduler import schedule


def test_scheduler_returns_decisions_for_72b_vllm_any():
    """
    针对文档中的例子:
    - 72B 模型 (~173GB)
    - engine = vllm
    - arch_requirement = any
    期望至少返回一个 Decision.
    """
    req = ScheduleRequest(
        model_id="Qwen/Qwen3-72B",
        model_params_b=72,
        engine="vllm",
        arch_requirement="any",
    )

    decisions = schedule(req)

    assert isinstance(decisions, list)
    assert len(decisions) >= 1


def test_scheduler_no_feasible_when_extremely_large_model():
    """
    非常大的模型(比如 1e6 B) 应该无法在当前集群资源下调度, schedule 返回空列表.
    """
    req = ScheduleRequest(
        model_id="Huge/Huge-Model",
        model_params_b=1_000_000,  # 1e6 B, 远超当前设备
        engine="vllm",
        arch_requirement="any",
    )

    decisions = schedule(req)

    assert decisions == []

