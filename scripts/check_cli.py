"""An explicit, synthetic provider check. Does not read any journal data."""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from dreamlit.models import AnalysisOutput
from dreamlit.providers.base import ProviderError, ProviderRequest
from dreamlit.providers.claude import ClaudeProvider
from dreamlit.providers.codex import CodexProvider


async def check(name):
    provider = CodexProvider(timeout=180) if name == "codex" else ClaudeProvider(timeout=180)
    request = ProviderRequest(
        "check",
        'Return summary "Ready", observations [], patterns []. Do not use tools.',
        {},
        AnalysisOutput.model_json_schema(),
    )
    with tempfile.TemporaryDirectory(prefix="dreamlit-check-") as folder:
        try:
            response = await provider.run(request, Path(folder))
            AnalysisOutput.model_validate(response.output)
            print(
                json.dumps(
                    {
                        "provider": name,
                        "status": "passed",
                        "model": response.model,
                        "usage": response.usage,
                    }
                )
            )
        except ProviderError as error:
            print(
                json.dumps(
                    {
                        "provider": name,
                        "status": "failed",
                        "code": error.code,
                        "message": error.message,
                    }
                )
            )
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["codex", "claude"], required=True)
    asyncio.run(check(parser.parse_args().provider))
