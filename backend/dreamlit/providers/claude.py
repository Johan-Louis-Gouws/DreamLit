import json
import shutil
from pathlib import Path

from .base import ProviderError, ProviderResponse, failure
from .process import run_process


def parse_claude(stdout):
    try:
        data = json.loads(stdout)
    except ValueError as error:
        raise ProviderError(
            "invalid_output", "Claude returned invalid structured output."
        ) from error
    if not isinstance(data, dict):
        raise ProviderError("invalid_output", "Claude returned an unexpected result.")
    if data.get("is_error"):
        raise failure(str(data.get("result", data.get("errors", ""))))
    output = data.get("structured_output")
    if not isinstance(output, dict):
        raise ProviderError(
            "invalid_output", "Claude did not return the required structured result."
        )
    return ProviderResponse(output, data.get("model"), data.get("usage"))


class ClaudeProvider:
    def __init__(self, timeout=240):
        self.timeout = timeout

    async def preflight(self):
        binary = shutil.which("claude")
        if not binary:
            return {"installed": False, "status": "missing_binary", "model": None}
        result = await run_process([binary, "--version"], "", Path.home(), 10)
        return {
            "installed": True,
            "status": "not_checked",
            "version": result.stdout.strip(),
            "model": None,
            "note": "Uses the CLI's configured model unless you set an override. Account access is checked only on request.",
        }

    async def run(self, request, job_dir):
        config = job_dir / "mcp.json"
        config.write_text('{"mcpServers":{}}')
        argv = [
            "claude",
            "--safe-mode",
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(request.output_schema),
            "--tools",
            "",
            "--strict-mcp-config",
            "--mcp-config",
            str(config),
            "--no-session-persistence",
            "--system-prompt",
            request.system_prompt,
        ]
        if request.model:
            argv += ["--model", request.model]
        payload = json.dumps({"task": request.task, "records": request.payload}, ensure_ascii=False)
        result = await run_process(argv, payload, job_dir, self.timeout)
        if result.returncode:
            raise failure(result.stderr + result.stdout)
        response = parse_claude(result.stdout)
        if request.model:
            response.model = request.model
        return response
