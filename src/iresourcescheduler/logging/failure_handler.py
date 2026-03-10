from __future__ import annotations

import json
from datetime import datetime, timezone

from iresourcescheduler.domain import FailureEvent


def handle_failure(event: FailureEvent) -> None:
    """
    统一失败处理接口.

    当前实现:
    - 在终端输出结构化日志, 作为“发送通知到 app”的占位实现.

    未来:
    - 可以在这里对接真正的通知通道(比如消息推送、Webhook、IM 机器人等),
      而不需要改动调度主流程.
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code": event.code,
        "message": event.message,
        "context": event.context or {},
    }
    print("[SCHEDULER_FAILURE_NOTIFY]", json.dumps(payload, ensure_ascii=False))

