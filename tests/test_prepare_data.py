import pytest

from fine_tuning.prepare_data import normalize_row


def test_instruction_format_becomes_chat():
    row = normalize_row(
        {"instruction": "What is an API?", "input": "", "output": "An interface."},
        1,
    )
    assert row["messages"][0]["role"] == "user"
    assert row["messages"][-1]["role"] == "assistant"


def test_chat_format_requires_assistant_target():
    with pytest.raises(ValueError):
        normalize_row({"messages": [{"role": "user", "content": "hello"}]}, 1)
