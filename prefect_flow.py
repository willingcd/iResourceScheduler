"""
Prefect 编排：将智能资源调度拆成多个 Task，全部写在本文件中。

依赖:
  pip install prefect
  pip install -e .   # 或设置 PYTHONPATH=src

运行示例:
  PYTHONPATH=src python prefect_flow.py

  或在代码中:
  from prefect_flow import resource_scheduler_flow
  resource_scheduler_flow(...)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 脚本直跑时确保能 import iresourcescheduler
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from prefect import flow, get_run_logger, task

from iresourcescheduler.compatibility import filter_compatible_clusters
from iresourcescheduler.domain import (
    ClusterSpec,
    ClusterState,
    Decision,
    EstimatedMemory,
    FailureEvent,
    Plan,
    ScheduleRequest,
)
from iresourcescheduler.estimator import estimate_memory
from iresourcescheduler.inventory import get_cluster_states, load_cluster_specs
from iresourcescheduler.inventory.state_cardinfo import build_cardinfo_authorization_headers
from iresourcescheduler.logging import handle_failure, log_decision
from iresourcescheduler.planner import plan_for_cluster
from iresourcescheduler.scheduler.scheduler import _build_decisions_from_plans


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(name="load-cluster-specs", retries=1, retry_delay_seconds=5)
def task_load_cluster_specs() -> List[ClusterSpec]:
    """从 YAML 加载集群静态规格."""
    logger = get_run_logger()
    specs = load_cluster_specs()
    logger.info("loaded %d cluster specs", len(specs))
    return specs


@task(name="estimate-memory")
def task_estimate_memory(request: ScheduleRequest) -> EstimatedMemory:
    """根据 model_params_b 估算显存需求."""
    logger = get_run_logger()
    est = estimate_memory(request)
    logger.info("estimated_memory_gb=%.2f", est.required_gb)
    return est


@task(name="get-cluster-states", retries=2, retry_delay_seconds=10)
def task_get_cluster_states(
    specs: List[ClusterSpec],
    api_base_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> List[ClusterState]:
    """调用 cardinfo（或 mock）获取各集群当前可用资源."""
    logger = get_run_logger()
    headers = build_cardinfo_authorization_headers(api_token=api_token)
    states = get_cluster_states(specs, base_url=api_base_url, headers=headers)
    logger.info("cluster states count=%d", len(states))
    return states


@task(name="filter-compatible-clusters")
def task_filter_compatible_clusters(
    request: ScheduleRequest,
    specs: List[ClusterSpec],
) -> List[ClusterSpec]:
    """按引擎/架构过滤候选集群."""
    logger = get_run_logger()
    candidates = filter_compatible_clusters(request, specs)
    logger.info("compatible candidates=%d", len(candidates))
    return candidates


@task(name="plan-for-each-cluster")
def task_plan_for_all_candidates(
    candidates: List[ClusterSpec],
    state_map: Dict[str, ClusterState],
    estimated: EstimatedMemory,
) -> List[Plan]:
    """为每个候选集群生成资源计划."""
    logger = get_run_logger()
    plans: List[Plan] = []
    for spec in candidates:
        state = state_map.get(spec.cluster_id)
        if state is None:
            continue
        plans.append(plan_for_cluster(spec, state, estimated))
    logger.info("generated %d plans", len(plans))
    return plans


@task(name="filter-feasible-plans")
def task_filter_feasible_plans(plans: List[Plan]) -> List[Plan]:
    """只保留 is_feasible 的 Plan."""
    feasible = [p for p in plans if p.is_feasible]
    get_run_logger().info("feasible plans=%d / %d", len(feasible), len(plans))
    return feasible


@task(name="build-decisions")
def task_build_decisions(feasible_plans: List[Plan]) -> List[Decision]:
    """同构去重，生成 Decision 列表."""
    decisions = _build_decisions_from_plans(feasible_plans)
    get_run_logger().info("decisions count=%d", len(decisions))
    return decisions


@task(name="log-decision")
def task_log_decision(
    request: ScheduleRequest,
    estimated: EstimatedMemory,
    decisions: List[Decision],
) -> None:
    """写入调度决策日志（终端 JSON）."""
    log_decision(request, estimated, decisions)


@task(name="handle-failure")
def task_handle_failure(event: FailureEvent) -> None:
    """统一失败通知占位（终端日志）."""
    handle_failure(event)


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(
    name="resource-scheduler-flow",
    log_prints=True,
)
def resource_scheduler_flow(
    model_params_b: float,
    engine: str,
    model_id: str = "",
    arch_requirement: str = "any",
    api_base_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> List[Decision]:
    """
    资源调度主流程（Prefect Flow）。

    参数与 CLI 含义一致；api_base_url / api_token 不传则使用环境变量
    CARDINFO_API_BASE_URL / AUTHORIZATION（或 CARDINFO_API_TOKEN，均为完整 Authorization 值）；测试可设 IRESCHEDULER_USE_MOCK_STATE=1。
    """
    logger = get_run_logger()
    request = ScheduleRequest(
        model_id=model_id or "unspecified",
        model_params_b=model_params_b,
        engine=engine,
        arch_requirement=arch_requirement,
    )

    specs_fut = task_load_cluster_specs.submit()
    estimated_fut = task_estimate_memory.submit(request)

    specs = specs_fut.result()
    if not specs:
        task_handle_failure(
            FailureEvent(code="NO_CLUSTER_SPECS", message="No cluster specs loaded", context={})
        )
        return []

    estimated = estimated_fut.result()

    states = task_get_cluster_states(specs, api_base_url=api_base_url, api_token=api_token)
    state_map = {s.cluster_id: s for s in states}

    candidates = task_filter_compatible_clusters(request, specs)
    if not candidates:
        task_handle_failure(
            FailureEvent(
                code="NO_COMPATIBLE_CLUSTERS",
                message="No compatible clusters for request",
                context={
                    "engine": request.engine,
                    "arch_requirement": request.arch_requirement,
                },
            )
        )
        return []

    plans = task_plan_for_all_candidates(candidates, state_map, estimated)
    feasible = task_filter_feasible_plans(plans)
    if not feasible:
        task_handle_failure(
            FailureEvent(
                code="NO_FEASIBLE_PLAN",
                message="No feasible plans for request",
                context={
                    "engine": request.engine,
                    "arch_requirement": request.arch_requirement,
                    "estimated_memory_gb": estimated.required_gb,
                },
            )
        )
        return []

    decisions = task_build_decisions(feasible)
    task_log_decision(request, estimated, decisions)

    logger.info("flow finished, %d decisions", len(decisions))
    return decisions


def _decisions_to_jsonable(decisions: List[Decision]) -> List[Dict[str, object]]:
    """Decision 中含 Enum，转为可 JSON 序列化的 dict."""
    out: List[Dict[str, object]] = []
    for d in decisions:
        row = dict(d.__dict__)
        p = row.get("parallelism")
        if hasattr(p, "value"):
            row["parallelism"] = p.value
        out.append(row)
    return out


def _main_cli() -> None:
    """简单命令行入口（可选）."""
    import argparse

    p = argparse.ArgumentParser(description="Run resource scheduler as Prefect flow")
    p.add_argument("--model-params-b", type=float, required=True)
    p.add_argument("--model-id", default="")
    p.add_argument("--engine", required=True)
    p.add_argument("--arch-requirement", default="any")
    p.add_argument("--api-base-url", default=None)
    p.add_argument("--api-token", default=None)
    args = p.parse_args()

    decisions = resource_scheduler_flow(
        model_params_b=args.model_params_b,
        engine=args.engine,
        model_id=args.model_id,
        arch_requirement=args.arch_requirement,
        api_base_url=args.api_base_url,
        api_token=args.api_token,
    )
    print(json.dumps(_decisions_to_jsonable(decisions), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main_cli()
