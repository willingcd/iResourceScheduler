import os
import sys
from pathlib import Path

# 测试时使用 mock 集群状态，不依赖真实 cardinfo 接口
os.environ["IRESCHEDULER_USE_MOCK_STATE"] = "1"


def _ensure_src_on_path() -> None:
    """
    确保 tests 可以通过 `import iresourcescheduler` 找到 src 包.
    """
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if src.exists():
        sys.path.insert(0, str(src))


_ensure_src_on_path()

