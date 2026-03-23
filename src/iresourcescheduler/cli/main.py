from __future__ import annotations

import argparse
import json

from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.scheduler import schedule


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Intelligent resource scheduler CLI")
    parser.add_argument(
        "--model-params-b",
        type=float,
        required=True,
        help="模型参数量(B)，如 72 表示 72B",
    )
    parser.add_argument(
        "--model-id",
        default="",
        help="可选，用于日志/追踪的模型标识（不参与参数量计算）",
    )
    parser.add_argument("--engine", required=True)
    parser.add_argument("--arch-requirement", default="any", help="any / ascend / nvidia")
    parser.add_argument("--api-base-url", default=None, help="cardinfo 接口根地址，如 https://your-ip（不传则读环境变量 CARDINFO_API_BASE_URL）")
    parser.add_argument("--api-token", default=None, help="cardinfo 接口 Authorization 完整值（与 export AUTHORIZATION 相同；不传则读环境变量）")

    args = parser.parse_args(argv)

    req = ScheduleRequest(
        model_id=args.model_id or "unspecified",
        model_params_b=args.model_params_b,
        engine=args.engine,
        arch_requirement=args.arch_requirement,
    )

    decisions = schedule(req, api_base_url=args.api_base_url, api_token=args.api_token)
    print(json.dumps([d.__dict__ for d in decisions], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
