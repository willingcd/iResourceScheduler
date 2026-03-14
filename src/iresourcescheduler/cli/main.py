from __future__ import annotations

import argparse
import json
import re

from iresourcescheduler.domain import ScheduleRequest
from iresourcescheduler.scheduler import schedule


def parse_model_params_b_from_model_id(model_id: str) -> float:
    """
    从 model_id 中提取「数字+B」里的数字，取最大值作为参数量(B)。
    例如 "Qwen3.5-397B-A17B" -> 397, 17 -> 397；"Qwen3-72B" -> 72。
    """
    # 匹配末尾为 B 的数字（整数或小数），如 397B、A17B 中的 17、1.5B
    matches = re.findall(r"(\d+(?:\.\d+)?)B", model_id, re.IGNORECASE)
    if not matches:
        raise ValueError(
            f"无法从 model_id 中解析参数量: {model_id!r}，未找到「数字+B」形式。请显式传入 --model-params-b。"
        )
    return max(float(m) for m in matches)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Intelligent resource scheduler CLI")
    parser.add_argument("--model-id", required=True, help="模型 ID，如 Qwen3.5-397B-A17B；若不传 --model-params-b 则从中解析参数量（取「数字B」中的最大数字）")
    parser.add_argument("--model-params-b", type=float, default=None, help="模型参数量(B)，不传则从 --model-id 解析（提取所有「数字B」中的数字取最大值）")
    parser.add_argument("--engine", required=True)
    parser.add_argument("--arch-requirement", default="any", help="any / ascend / nvidia")
    parser.add_argument("--api-base-url", default=None, help="cardinfo 接口根地址，如 https://your-ip（不传则读环境变量 CARDINFO_API_BASE_URL）")
    parser.add_argument("--api-token", default=None, help="cardinfo 接口 Authorization Bearer 令牌（不传则读环境变量 CARDINFO_API_TOKEN）")

    args = parser.parse_args(argv)

    model_params_b = args.model_params_b
    if model_params_b is None:
        model_params_b = parse_model_params_b_from_model_id(args.model_id)

    req = ScheduleRequest(
        model_id=args.model_id,
        model_params_b=model_params_b,
        engine=args.engine,
        arch_requirement=args.arch_requirement,
    )

    decisions = schedule(req, api_base_url=args.api_base_url, api_token=args.api_token)
    print(json.dumps([d.__dict__ for d in decisions], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

