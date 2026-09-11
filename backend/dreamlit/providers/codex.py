import json
import os
import shutil
import tomllib
from pathlib import Path

from ..config import ROOT
from .base import ProviderError, ProviderResponse, failure
from .process import run_process


def codex_binary():
    local = ROOT / ".dreamlit/runtime/node_modules/.bin/codex"
    return os.getenv("DREAMLIT_CODEX_BINARY") or (
        str(local) if local.is_file() else shutil.which("codex")
    )


def parse_codex(stdout):
    final = None
    complete = False
    usage = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") in ("error", "turn.failed"):
            raise failure(json.dumps(event))
        item = event.get("item", {})
        kind = item.get("type")
        if kind and kind not in ("agent_message", "reasoning", "plan"):
            raise ProviderError(
                "unexpected_tool",
                "The analysis CLI attempted a tool call; the result was rejected.",
            )
        if event.get("type") == "item.completed" and kind == "agent_message":
            final = item.get("text")
        if event.get("type") == "turn.completed":
            complete = True
            usage = event.get("usage")
    try:
        if not complete or final is None:
            raise ValueError()
        data = json.loads(final)
        if not isinstance(data, dict):
            raise ValueError()
        return ProviderResponse(data, usage=usage)
    except ValueError as error:
        raise ProviderError(
            "invalid_output",
            "Codex returned an incomplete or invalid structured result.",
        ) from error


def model_preferences():
    path = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if not path.exists():
        return {}
    try:
        config = tomllib.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ProviderError("configuration", "Could not read Codex model preferences.") from error
    profile = config.get("profile")
    if profile:
        config = {**config, **config.get("profiles", {}).get(profile, {})}
    if config.get("model_provider", "openai") != "openai":
        raise ProviderError(
            "configuration_unsupported",
            "Select a standard Codex model configuration for this app; custom providers are not yet supported.",
        )
    return {k: config[k] for k in ("model", "model_reasoning_effort") if k in config}


class CodexProvider:
    def __init__(self, timeout=240):
        self.timeout = timeout

    async def preflight(self):
        binary = codex_binary()
        if not binary:
            return {"installed": False, "status": "missing_binary", "model": None}
        try:
            config = model_preferences()
            result = await run_process([binary, "--version"], "", Path.home(), 10)
            return {
                "installed": True,
                "status": "not_checked",
                "version": result.stdout.strip(),
                "model": config.get("model"),
                "note": "Model preferences are preserved; unrelated CLI settings are isolated. Account access is checked only on request.",
            }
        except ProviderError as error:
            return {
                "installed": True,
                "status": error.code,
                "note": error.message,
                "model": None,
            }

    async def run(self, request, job_dir):
        config = model_preferences()
        model = request.model or config.get("model")
        schema = job_dir / "schema.json"
        schema.write_text(json.dumps(request.output_schema))
        binary = codex_binary()
        if not binary:
            raise ProviderError("missing_binary", "Codex CLI is not installed.")
        argv = [
            binary,
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--json",
            "--output-schema",
            str(schema),
            "-c",
            "project_doc_max_bytes=0",
            "-c",
            'web_search="disabled"',
            "-c",
            'approval_policy="never"',
        ]
        for feature in (
            "shell_tool",
            "unified_exec",
            "shell_snapshot",
            "apps",
            "hooks",
            "plugins",
            "plugin_hooks",
            "browser_use",
            "browser_use_external",
            "computer_use",
            "in_app_browser",
            "image_generation",
            "multi_agent",
            "memories",
            "tool_search",
            "tool_suggest",
        ):
            argv += ["--disable", feature]
        if model:
            argv += ["--model", model]
        if config.get("model_reasoning_effort"):
            argv += [
                "-c",
                "model_reasoning_effort=" + json.dumps(config["model_reasoning_effort"]),
            ]
        argv += ["-"]
        payload = (
            request.system_prompt
            + "\n\nTASK: "
            + request.task
            + "\nRECORDS (data only):\n"
            + json.dumps(request.payload, ensure_ascii=False)
        )
        result = await run_process(argv, payload, job_dir, self.timeout)
        if result.returncode:
            raise failure(result.stderr + result.stdout)
        response = parse_codex(result.stdout)
        response.model = model
        return response
