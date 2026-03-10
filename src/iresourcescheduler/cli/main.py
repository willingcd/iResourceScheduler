from __future__ import annotations

import argparse
import json

from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.scheduler import schedule


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Intelligent resource scheduler CLI")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-params-b", type=float, required=True, help="Model params in B (billion)")
    parser.add_argument("--engine", required=True)
    parser.add_argument("--arch-requirement", default="any", help="any / ascend / nvidia")

    args = parser.parse_args(argv)

    req = ScheduleRequest(
        model_id=args.model_id,
        model_params_b=args.model_params_b,
        engine=args.engine,
        arch_requirement=args.arch_requirement,
    )

    decisions = schedule(req)
    print(json.dumps([d.__dict__ for d in decisions], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

