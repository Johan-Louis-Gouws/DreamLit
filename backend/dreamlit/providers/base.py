from dataclasses import dataclass


@dataclass
class ProviderRequest:
    task: str
    system_prompt: str
    payload: dict
    output_schema: dict
    model: str | None = None


@dataclass
class ProviderResponse:
    output: dict
    model: str | None = None
    usage: dict | None = None


class ProviderError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def failure(text):
    text = text.lower()
    if "requires a newer version" in text or "please upgrade" in text:
        return ProviderError(
            "cli_outdated",
            "This model requires a newer Codex CLI. Update the app runtime or select a compatible model explicitly.",
        )
    if any(word in text for word in ("usage limit", "rate limit", "quota", "credit", "429")):
        return ProviderError(
            "usage_limit",
            "Provider usage limit reached. Retry when your account has capacity.",
        )
    if any(
        word in text
        for word in (
            "not logged",
            "unauthorized",
            "authentication",
            "oauth",
            "401",
            "sign in",
            "log in",
            "api key",
        )
    ):
        return ProviderError("authentication", "Sign in through this provider's CLI, then retry.")
    if any(
        word in text
        for word in (
            "config",
            "unknown variant",
            "unknown argument",
            "unexpected argument",
        )
    ):
        return ProviderError(
            "configuration",
            "The CLI configuration is incompatible. Check provider setup.",
        )
    if any(word in text for word in ("network", "connect", "resolve", "timed out")):
        return ProviderError(
            "network",
            "The provider could not be reached. Check your connection and retry.",
        )
    return ProviderError(
        "provider_failed",
        "The CLI did not complete the request. Check its login and account status.",
    )
