import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """
    确保 tests 可以通过 `import iresourcescheduler` 找到 src 包.
    """
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if src.exists():
        sys.path.insert(0, str(src))


_ensure_src_on_path()

