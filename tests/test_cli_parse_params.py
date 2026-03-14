"""从 model_id 解析 model_params_b 的逻辑."""
import pytest
from iresourcescheduler.cli.main import parse_model_params_b_from_model_id


def test_parse_single_b():
    assert parse_model_params_b_from_model_id("Qwen3-72B") == 72.0


def test_parse_multiple_take_max():
    assert parse_model_params_b_from_model_id("Qwen3.5-397B-A17B") == 397.0


def test_parse_integer_and_float():
    assert parse_model_params_b_from_model_id("Model-7B") == 7.0
    assert parse_model_params_b_from_model_id("Model-1.5B") == 1.5


def test_parse_no_b_raises():
    with pytest.raises(ValueError, match="无法从 model_id 中解析参数量"):
        parse_model_params_b_from_model_id("Qwen3-no-number")
