import asyncio
import json
import sys

import pytest
from dreamlit.providers.base import ProviderError
from dreamlit.providers.claude import parse_claude
from dreamlit.providers.codex import parse_codex
from dreamlit.providers.process import run_process


def test_prompt_is_never_shell_interpolated(tmp_path):
    value = "A $(touch sentinel) appeared."
    result = asyncio.run(
        run_process(
            [sys.executable, "-c", "import sys; print(sys.stdin.read())"],
            value,
            tmp_path,
            5,
        )
    )
    assert result.stdout.strip() == value
    assert not (tmp_path / "sentinel").exists()


def test_process_timeout(tmp_path):
    with pytest.raises(ProviderError) as error:
        asyncio.run(
            run_process([sys.executable, "-c", "import time; time.sleep(30)"], "", tmp_path, 0.1)
        )
    assert error.value.code == "timeout"


def test_realistic_envelopes_and_failures():
    value = {"summary": "hello", "observations": [], "patterns": []}
    result = parse_claude(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "structured_output": value,
                "usage": {"input_tokens": 1},
            }
        )
    )
    assert result.output == value
    event = {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": json.dumps(value)},
    }
    assert (
        parse_codex(
            json.dumps(event) + "\n" + json.dumps({"type": "turn.completed", "usage": {}})
        ).output
        == value
    )
    with pytest.raises(ProviderError):
        parse_claude(json.dumps({"type": "result", "is_error": True, "result": "usage limit"}))
    with pytest.raises(ProviderError):
        parse_codex(json.dumps({"type": "turn.failed", "error": {"message": "network error"}}))


def test_tool_events_are_rejected():
    event = {
        "type": "item.completed",
        "item": {"type": "command_execution", "command": "ls"},
    }
    with pytest.raises(ProviderError, match="tool"):
        parse_codex(json.dumps(event))
